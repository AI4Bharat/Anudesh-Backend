from tablib import Dataset
from django.apps import apps
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.views import APIView
from django_celery_results.models import TaskResult

from urllib.parse import parse_qsl

from filters import filter
from projects.serializers import ProjectSerializer
from users.models import User
from .models import *
from .serializers import *
from .resources import RESOURCE_MAP
from . import resources
from .permissions import DatasetInstancePermission


## Utility functions used inside the view functions
def get_project_export_status(pk):
    """Function to return status of the project export background task.

    Args:
        pk (int): Primary key of the project

    Returns:
        str: Status of the project export
        str: Date when the last time project was exported
    """

    # Create the keyword argument for project ID
    project_id_keyword_arg = "'project_id': " + "'" + str(pk) + "'" + ","

    # Check the celery project export status
    task_queryset = TaskResult.objects.filter(
        task_name__in=[
            'projects.tasks.export_project_in_place',
            'projects.tasks.export_project_new_record'
        ],
        # task_name = 'projects.tasks.export_project_in_place',
        task_kwargs__contains=project_id_keyword_arg,
    )

    # If the celery TaskResults table returns
    if task_queryset:

        # Sort the tasks by newest items first by date
        task_queryset = task_queryset.order_by('-date_done')

        # Get the export task status and last update date
        task_status = task_queryset.first().as_dict()['status']
        task_datetime = task_queryset.first().as_dict()['date_done']

        # Extract date and time from the datetime object
        task_date = task_datetime.date()
        task_time = str(task_datetime.time().replace(microsecond=0)) + " UTC"

        return task_status, task_date, task_time

    return "Success", "Synchronously Completed. No Date.", "Synchronously Completed. No Time."

# Create your views here.
class DatasetInstanceViewSet(viewsets.ModelViewSet):
    '''
    ViewSet for Dataset Instance
    '''
    queryset = DatasetInstance.objects.all()
    permission_classes = (DatasetInstancePermission, )

    def get_serializer_class(self):
        if self.action == 'upload':
            return DatasetInstanceUploadSerializer
        return DatasetInstanceSerializer

    def list(self, request, *args, **kwargs):
        # Org Owners and superusers see all datasets
        if request.user.role == User.ORGANIZAION_OWNER or request.user.is_superuser:
            queryset = DatasetInstance.objects.all()
        # Managers only see datasets that they are added to and public datasets
        else:
            queryset = DatasetInstance.objects.filter(Q(public_to_managers=True) | Q(users__id=request.user.id))

        # Filter the queryset based on the query params
        if "dataset_type" in dict(request.query_params):
            queryset = queryset.filter(dataset_type__exact=request.query_params["dataset_type"])

        # Serialize the distinct items and sort by instance ID
        serializer = DatasetInstanceSerializer(queryset.distinct().order_by('instance_id'), many=True)
        return Response(serializer.data)

    @action(methods=['GET'], detail=True, name="Download Dataset in CSV format")
    def download(self, request, pk):
        """
        View to download a dataset in CSV format
        URL: /data/instances/<instance-id>/download/
        Accepted methods: GET
        """
        try:
            # Get the dataset instance for the id
            dataset_instance = DatasetInstance.objects.get(instance_id=pk)
        except DatasetInstance.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        dataset_model = apps.get_model('dataset', dataset_instance.dataset_type)
        data_items = dataset_model.objects.filter(instance_id=pk)
        dataset_resource = getattr(resources, dataset_instance.dataset_type+"Resource")
        exported_items = dataset_resource().export_as_generator(data_items)
        return StreamingHttpResponse(exported_items, status=status.HTTP_200_OK, content_type='text/csv')


    @action(methods=['POST'], detail=True, name="Upload CSV Dataset")
    def upload(self, request, pk):
        '''
        View to upload a dataset in CSV format
        URL: /data/instances/<instance-id>/upload/
        Accepted methods: POST
        '''
        # Define list of accepted file formats
        ACCEPTED_FILETYPES = ['csv', 'tsv', 'json', 'yaml', 'xls', 'xlsx']

        # Get the dataset type using the instance ID
        dataset_type = get_object_or_404(DatasetInstance, pk=pk).dataset_type

        # Fetch the file from the POST request body (key is dataset)
        if 'dataset' not in request.FILES:
            return Response({
                "message": "Please provide a file with key 'dataset'.",
            }, status=status.HTTP_400_BAD_REQUEST)
        dataset = request.FILES['dataset']
        content_type = dataset.name.split('.')[-1]

        # Ensure that the content type is accepted, return error otherwise
        if content_type not in ACCEPTED_FILETYPES:
            return Response({
                "message": f"Invalid Dataset File. Only accepts the following file formats: {ACCEPTED_FILETYPES}",
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create a new tablib Dataset and load the data into this dataset
        if content_type in ['xls', 'xlsx']:
            imported_data = Dataset().load(dataset.read(), format=content_type)
        else:
            imported_data = Dataset().load(dataset.read().decode(), format=content_type)

        # Add the instance_id column to all rows in the dataset
        imported_data.append_col([pk]*len(imported_data), header="instance_id")

        # Declare the appropriate resource map based on dataset type
        resource = RESOURCE_MAP[dataset_type]()

        # Import the data into the database
        try:
            resource.import_data(imported_data, raise_errors=True)
        # If validation checks fail, raise the Exception
        except Exception as e:
            return Response({
                "message": "Dataset validation failed.",
                "exception": e
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": f"Uploaded {dataset_type} data to Dataset {pk}",
        }, status=status.HTTP_201_CREATED)

    @action(methods=['GET'], detail=True, name="List all Projects using Dataset")
    def projects(self, request, pk):
        '''
        View to list all projects using a dataset
        URL: /data/instances/<instance-id>/projects/
        Accepted methods: GET
        '''
        # Get the projects using the instance ID
        projects = apps.get_model('projects', 'Project').objects.filter(dataset_id=pk)

        # Serialize the projects and return them to the frontend
        serializer = ProjectSerializer(projects, many=True)

        # Add new fields to the serializer data to show project exprot status and date
        for project in serializer.data:

            # Get project export status details
            project_export_status, last_project_export_date, last_project_export_time = get_project_export_status(project.get('id'))
            project["last_project_export_status"] = project_export_status
            project["last_project_export_date"] = last_project_export_date
            project["last_project_export_time"] = last_project_export_time

        return Response(serializer.data)


class DatasetItemsViewSet(viewsets.ModelViewSet):
    '''
    ViewSet for Dataset Items
    '''
    queryset = DatasetBase.objects.all()
    serializer_class = DatasetItemsSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )

    @action(detail=False, methods=['POST'], name='Get data Items')
    def get_data_items(self, request, *args, **kwargs):
        try:
            dataset_instance_ids = request.data.get('instance_ids')
            dataset_type = request.data.get('dataset_type',"")
            if type(dataset_instance_ids) != list:
                dataset_instance_ids = [dataset_instance_ids]
            filter_string = request.data.get('filter_string')
            #  Get dataset type from first dataset instance if dataset_type not passed in json data from frontend
            if dataset_type=="":
                dataset_type = DatasetInstance.objects.get(instance_id=dataset_instance_ids[0]).dataset_type
            dataset_model = apps.get_model('dataset', dataset_type)
            data_items = dataset_model.objects.filter(instance_id__in=dataset_instance_ids)
            query_params = dict(parse_qsl(filter_string))
            query_params = filter.fix_booleans_in_dict(query_params)
            filtered_set = filter.filter_using_dict_and_queryset(query_params, data_items)
            # filtered_data = filtered_set.values()
            # serializer = DatasetItemsSerializer(filtered_set, many=True)
            page = request.GET.get('page')
            try:
                page = self.paginate_queryset(filtered_set)
            except Exception as e:
                page = []
                data = page
                return Response({
                    "status": status.HTTP_200_OK,
                    "message": 'No more record.',
                    #TODO: should be results. Needs testing to be sure.
                    "data": data
                })

            if page is not None:
                datset_serializer=SERIALIZER_MAP[dataset_type]
                serializer=datset_serializer(page,many=True)
                data=serializer.data
                return self.get_paginated_response(data)

            return Response({
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Error fetching data items!"
            })
        except:
            return Response({
                "status":status.HTTP_400_BAD_REQUEST,
                "message":"Error fetching data items!"
                })
        # return Response(filtered_data)


class DatasetTypeView(APIView):
    '''
    ViewSet for Dataset Type
    '''
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def get(self, request, dataset_type):
        model = apps.get_model('dataset', dataset_type)
        fields = model._meta.get_fields()
        dict = {}
        for field in fields:
            try:
                dict[field.name] = {'name':str(field.get_internal_type()),'choices':vars(field)['choices']}
            except:
                dict[field.name] = {'name':str(field.get_internal_type()),'choices':None}
        return Response(dict,status=status.HTTP_200_OK)


# class SentenceTextViewSet(viewsets.ModelViewSet):
#     queryset = SentenceText.objects.all()
#     serializer_class = SentenceTextSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class SpeechCollectionViewset(viewsets.ModelViewSet):
#     queryset = SpeechCollection.objects.all()
#     serializer_class = SpeechCollectionSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class SpeechRecognitionViewSet(viewsets.ModelViewSet):
#     queryset = SpeechRecognition.objects.all()
#     serializer_class = SpeechRecognitionSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )


# class MonolingualViewSet(viewsets.ModelViewSet):
#     queryset = Monolingual.objects.all()
#     serializer_class = MonolingualSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class TranslationViewSet(viewsets.ModelViewSet):
#     queryset = Translation.objects.all()
#     serializer_class = TranslationSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class OCRViewSet(viewsets.ModelViewSet):
#     queryset = OCR.objects.all()
#     serializer_class = OCRSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class VideoViewSet(viewsets.ModelViewSet):
#     queryset = Video.objects.all()
#     serializer_class = VideoSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class VideoChunkViewSet(viewsets.ModelViewSet):
#     queryset = VideoChunk.objects.all()
#     serializer_class = VideoChunkSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

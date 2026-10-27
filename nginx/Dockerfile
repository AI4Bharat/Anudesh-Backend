# 1.26 is the current stable series; it includes HTTP/2 improvements and
# security fixes over 1.23.
FROM nginx:1.26-alpine

RUN apk add --no-cache openssl

# Override the base image's main nginx.conf so worker_processes, worker
# connections, and other main/events-context directives take effect.
COPY nginx.conf /etc/nginx/nginx.conf

COPY default.conf /etc/nginx/conf.d/
COPY gzip.conf options-ssl-nginx.conf hsts.conf proxy-llm.conf /etc/nginx/includes/
COPY site.conf.tpl /customization/
COPY nginx.sh /customization/

RUN chmod +x /customization/nginx.sh

EXPOSE 80

CMD ["/customization/nginx.sh"]
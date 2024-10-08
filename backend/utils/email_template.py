def send_email_template_with_attachment(subject, username, message):
    style_string = """
            *{ margin: 0; 
            padding: 0;
            }
            body {
            font-family: "Arial", sans-serif;
            background-color: #f2f8f8;
            margin: 0;
            padding: 0;
            padding-top: 2rem;
            }
            .container {
            background-color: #fff;
            border: solid 1px #e1e1e1;
            border-radius: 2px;
            padding: 1.4rem;
            max-width: 380px;
            margin: auto;
            }
            .header {
            width: fit-content;
            margin: auto;
            }
            h1 {
            font-size: 1.2rem;
            font-weight: 300;
            margin: 1rem 0;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            }
            p {
            font-size: 0.8rem;
            color: #222;
            margin: 0.8rem 0;
            }
            .primary {
            color: #18621f;
            }
            .footer {
            margin-top: 1rem;
            font-size: 0.9rem;
            }
            .footer > * {
            font-size: inherit;
            }
    """

    html_code = f""" 
    <!DOCTYPE html>
                <html lang="en">
                <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>{subject}</title>
                <style>
                {style_string}
                </style>
                </head>
                <body>
                <div class="container">
                <header class="header">
                <h3>{subject}</h3>
                </header>
                <main>
                <div style="margin: 1rem auto; width: fit-content">
                </div>
                <div>
                <p>
                    Dear {username},
                </p>
                <p>                
                {message}
                <p style="font-style: italic">
                    Thanks for contributing on Anudesh!
                </p>
                <p style="font-size: 10px; color:grey">
                This email was intended for {username} If you received it by mistake, please delete it and notify the sender immediately. 
                </p>
                </div>
                </main>
                <footer class="footer">
                <p style="font-size: 0.8rem;">
                Best Regards,<br />
                Anudesh Admin
                </p>
                </footer>
                </div>
                </body>
                </html>
    """
    return html_code


def send_email_template(subject, message):
    style_string = """
            *{ margin: 0; 
            padding: 0;
            }
            body {
            font-family: "Arial", sans-serif;
            background-color: #f2f8f8;
            margin: 0;
            padding: 0;
            padding-top: 2rem;
            }
            .container {
            background-color: #fff;
            border: solid 1px #e1e1e1;
            border-radius: 2px;
            padding: 1.4rem;
            max-width: 380px;
            margin: auto;
            }
            .header {
            width: fit-content;
            margin: auto;
            }
            h1 {
            font-size: 1.2rem;
            font-weight: 300;
            margin: 1rem 0;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            }
            p {
            font-size: 0.8rem;
            color: #222;
            margin: 0.8rem 0;
            }
            .primary {
            color: #18621f;
            }
            .footer {
            margin-top: 1rem;
            font-size: 0.9rem;
            }
            .footer > * {
            font-size: inherit;
            }
    """

    html_code = f""" 
    <!DOCTYPE html>
                <html lang="en">
                <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>{subject}</title>
                <style>
                {style_string}
                </style>
                </head>
                <body>
                <div class="container">
                <header class="header">
                <h3>{subject}</h3>
                </header>
                <main>
                <div style="margin: 1rem auto; width: fit-content">
                </div>
                <div>
                    <p>
                        Dear User,
                    </p>
                              
                {message}
                <p style="font-size: 10px; color:grey">
                This is an automated email. Please do not reply to this email.
                </p>
                </div>
                </main>
                <footer class="footer">
                <p style="font-size: 0.8rem;">
                Best Regards,<br />
                Shoonya Admin
                </p>
                </footer>
                </div>
                </body>
                </html>
    """
    return html_code

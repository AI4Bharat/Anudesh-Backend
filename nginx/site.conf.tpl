server {
    listen 80;
    server_name ${domain};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot/${domain};
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    # http2 enables HTTP/2 multiplexing: multiple requests share a single
    # TLS connection, cutting handshake overhead under concurrent LLM calls.
    listen 443 ssl http2;
    server_name ${domain};

    ssl_certificate /etc/nginx/sites/ssl/dummy/${domain}/fullchain.pem;
    ssl_certificate_key /etc/nginx/sites/ssl/dummy/${domain}/privkey.pem;

    include /etc/nginx/includes/options-ssl-nginx.conf;

    ssl_dhparam /etc/nginx/sites/ssl/ssl-dhparams.pem;

    include /etc/nginx/includes/hsts.conf;

    # ------------------------------------------------------------------
    # Proxy defaults — inherited by every location block in the vhost.
    # ------------------------------------------------------------------

    # Use HTTP/1.1 to the upstream so the keepalive pool in web_backend
    # works (HTTP/1.0 closes the connection after each request).
    proxy_http_version  1.1;
    # Clear the Connection header so nginx doesn't forward "close" to
    # Gunicorn, which would defeat upstream keepalive.
    proxy_set_header    Connection "";

    # Standard forwarding headers.
    proxy_set_header    Host               $host;
    proxy_set_header    X-Real-IP          $remote_addr;
    proxy_set_header    X-Forwarded-For    $proxy_add_x_forwarded_for;
    proxy_set_header    X-Forwarded-Proto  $scheme;

    # LLM API calls can take 30–120 s. These timeouts match Gunicorn's
    # --timeout 300 so nginx never drops a valid in-flight LLM request.
    proxy_connect_timeout   10s;   # TCP connect to Gunicorn (should be fast)
    proxy_send_timeout      300s;  # time to finish sending request to Gunicorn
    proxy_read_timeout      300s;  # time to wait for Gunicorn's full response

    # Buffer LLM responses in nginx memory so Gunicorn workers are freed
    # as soon as they produce the response, not when the (potentially slow)
    # client finishes downloading it.
    proxy_buffering             on;
    proxy_buffer_size           16k;   # header buffer
    proxy_buffers               16 32k; # body buffers (total 512 k per req)
    proxy_busy_buffers_size     64k;

    include /etc/nginx/vhosts/${domain}.conf;
}

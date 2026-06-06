FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY nodes.json /usr/share/nginx/html/nodes.json
COPY og.png /usr/share/nginx/html/og.png
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

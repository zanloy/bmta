FROM bitnami/python:3.8.10-prod

ENV LANG='en_US.UTF-8'
LABEL maintainer='Zan Loy <zan.loy@gmail.com>'

RUN pip3 install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org pipenv

COPY bmta.py Pipfile Pipfile.lock /app/
RUN pipenv install

CMD ["pipenv", "run", "./bmta.py"]
FROM python:3.9

#
WORKDIR /neshkola

#
COPY requirements.txt /neshkola/requirements.txt

COPY neshkola.service /etc/systemd/system/

#
RUN pip install --no-cache-dir --upgrade -r /neshkola/requirements.txt

#
COPY app /neshkola/app

#
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
FROM Python:3.9.0
RUN mkdir /bot
COPY requirements.txt /bot/
RUN python -m pip install -r /bot/requirements.txt
COPY bot.py /bot/
COPY models.py /bot/
COPY handlers.py /bot/
COPY settings.py /bot/
ADD img /bot/img
WORKDIR /bot
ENTRYPOINT ["python", "bot.py"]

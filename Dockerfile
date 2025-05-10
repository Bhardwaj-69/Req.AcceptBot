# Using Python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install required dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy Bot and Flask app code
COPY . .

# For environment variables
ENV PYTHONUNBUFFERED 1

# Command to run both Flask app and Telegram bot
CMD ["sh", "-c", "gunicorn app:app & python3 bot.py"]

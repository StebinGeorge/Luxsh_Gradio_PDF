# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variables
ENV NAME GradioApp

# Set default value for GRADIO_SERVER_PORT argument
ARG GRADIO_SERVER_PORT=7860
ENV GRADIO_SERVER_PORT=${GRADIO_SERVER_PORT}

# Copy the Google Cloud credentials file into the container
COPY ./subtle-odyssey-400507-0b24c38d6538.json /app/subtle-odyssey-400507-0b24c38d6538.json

# Set environment variable for Google Cloud credentials
ENV GOOGLE_APPLICATION_CREDENTIALS /app/subtle-odyssey-400507-0b24c38d6538.json

# Ensure the 'flagged' directory is created with proper permissions
RUN mkdir /app/flagged && chmod 777 /app/flagged

# Additional environment variables for Gradio configuration

# Run app.py when the container launches
CMD ["python", "app.py"]

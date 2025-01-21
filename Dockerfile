# Use the official Python image from the Docker Hub
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip3 install -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 5000

ENV MYSQL_HOST="host.docker.internal"

# Run the application
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]
# Use the official Python image as the base image
FROM python:3.10.13

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Set the command to run the Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "api.app:app"]
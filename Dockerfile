# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project's code into the container
COPY . /app/

# Expose the port the app runs on
EXPOSE 8000

# Run the application using Gunicorn
# Replace 'your_project_name.wsgi:application' with the actual path to your WSGI file.
# For example, if your project is LabLedger-Backend, it would be LabLedger-Backend.wsgi:application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "LabLedger.wsgi:application"]
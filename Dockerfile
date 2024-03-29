# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /github_stock

# Copy the current directory contents into the container at /app
COPY . /github_stock/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# Expose the port the app runs on
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py

# Run app.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0"]

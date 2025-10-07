#!/bin/bash

echo "========================================="
echo "Starting LabLedger Update Process"
echo "========================================="

# Navigate to project directory
cd /var/www/projects/LabLedger-Backend

# Create venv
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Pull latest code
echo "Pulling latest code from GitHub..."
git pull

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Check for errors
echo "Checking for Django errors..."
python manage.py check

# Set permissions
echo "Setting permissions..."
sudo chown -R ubuntu:www-data /var/www/projects/LabLedger-Backend
sudo chmod -R 755 /var/www/projects/LabLedger-Backend
sudo chmod -R 775 /var/www/projects/LabLedger-Backend/media
sudo chmod -R 775 /var/www/projects/LabLedger-Backend/logs

# Restart services
echo "Restarting Gunicorn..."
sudo systemctl restart gunicorn

echo "Restarting Nginx..."
sudo systemctl restart nginx

# Check service status
echo "========================================="
echo "Checking service status..."
echo "========================================="
sudo systemctl status gunicorn --no-pager
sudo systemctl status nginx --no-pager

echo "========================================="
echo "Update Complete!"
echo "========================================="

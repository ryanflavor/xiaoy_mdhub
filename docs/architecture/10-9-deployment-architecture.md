### **9. Deployment Architecture**

* **Backend**: The `apps/api` service will be packaged into a Docker image via a `Dockerfile`. This image, along with database containers, will be defined in a `docker-compose.prod.yml` file to be run on the Ubuntu host.
* **Frontend**: The `apps/web` application will be linked to a Vercel project. Every push to the `main` branch will trigger an automatic build and deployment to production.
* **Scheduling**: A `cron` job on the Ubuntu host will execute `docker-compose -f docker-compose.prod.yml up -d` and `down` commands based on the required trading schedule.

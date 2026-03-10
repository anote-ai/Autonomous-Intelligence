# Codebase Development Environment

**1. Initial setup**

Clone the repo:
``` py
$ git clone https://github.com/nv78/Autonomous-Intelligence
```
You should have a folder that looks as follows:

![directory](https://github.com/nv78/Autonomous-Intelligence/blob/main/materials/assets/codebase/directory.png?raw=True)

**2. Frontend - setting up React**

If you haven’t installed/used React before and you do not have Node.js installed on your computer, follow instructions here.

Change directory into the frontend folder:

``` py
$ cd frontend
```
Then run:

``` py
$ npm install
```

Once that is done, to start the frontend:

```
$ npm start
```

Navigate to localhost on your browser, and you should see the frontend rendered.

**3. Backend**
**Prefer way of installation**

1. Make sure you have Docker installed on your system. You can download it from [Docker's official website](https://www.docker.com/products/docker-desktop/).

2. Build and run the Docker containers:
```bash
$ docker-compose up --build
```

This will start both the frontend and backend services in Docker containers.

3. Access the application:
- Frontend will be available at: http://localhost:3000
- Backend will be available at: http://localhost:5000

4. Database Setup in Docker (automated if require please follow the following step to setup database):
You might need to initialize the database inside the Docker container. To do this:

```bash
# Get into the backend container
$ docker compose exec <container_name> sh

# Once inside the container, navigate to the database directory
$ cd database

# Initialize the database
$ python init_db_dev.py
```

5. To stop the Docker containers:
```bash
$ docker-compose down
```

Note: If you make changes to the code, you'll need to rebuild the containers using `docker-compose up --build` again.

Common Docker Issues:
- If you get permission errors, you might need to run Docker commands with `sudo`
- If ports are already in use, make sure no other services are running on ports 3000 and 5000
- If the database connection fails, ensure the MySQL container is running properly


**Legacy codebase setup for backend**
To best manage Python libraries and dependencies, use a [conda virtual environment](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)

Now create a new conda environment: 
``` py
$ conda create -n anote python=3.10.13
```
Make sure you are in the folder “server” by doing 
``` py
cd server
```

Then do:
``` py
$ pip install -r requirements.txt
```

Now add the flask environment variables: 
``` py
$ export APP_ENV=local
$ export IS_PROD=false
```

To check that it’s working, run:
``` py
$ flask run
```

You should get an output in your terminal:
![directory](https://github.com/nv78/Autonomous-Intelligence/blob/main/materials/assets/codebase/flask.png?raw=True)

**4. Setting up MySQL environment**

Download version of [MYSQL Workbench](https://dev.mysql.com/downloads/mysql/) compatible with your OS

``` py
$ mysql -u root -p
$ create database agents;
```

Go to the server/database folder and run the initialization of the db: 
``` py
$ cd server/database
$ python init_db_dev.py
```

Check that it worked:
``` py
$ mysql -u root -p
```
Log into the mysql CLI then run from inside the mysql CLI: 
``` py
mysql> use agents;
mysql> show tables;
```

It should look like this:
![directory](https://github.com/nv78/Autonomous-Intelligence/blob/main/materials/assets/codebase/sqltable.png?raw=True)

**5. Running the Application**
To run the web app, you need two terminal windows/tabs. On one, you will run the frontend: 
``` py
$ npm start
```
On the other, you will run the backend:
``` py
$ flask run
```
To check they are both working, on localhost on your browser, try to login using your google account using google auth.

**6. Running the SDK Locally**
To run the SDK, you need to run the backend using
``` py
$ flask run
```
You will also need to get the API key locally. To do so, run the frontend, log in, then click your profile and select API:

![directory](https://github.com/nv78/Autonomous-Intelligence/blob/main/materials/assets/codebase/nav.png?raw=True)

Create a new API key and store this somewhere
To test the SDK locally, you will need this API key. Replace it on line 15.

![directory](https://github.com/nv78/Autonomous-Intelligence/blob/main/materials/assets/codebase/sdk.png?raw=True)

**7. Common bugs/debugging techniques**

If your backend isn’t working properly, make sure you did (even if you did it at the start, might have to redo it):
``` py
$ export APP_ENV=local
$ export IS_PROD=false
```
If flask run doesn’t work, try: 
``` py
python -m flask run
```

If frontend doesn't work, try:
``` py
npm install --force
```

You might need to install JDK8 for Apache Tika for uploading files.

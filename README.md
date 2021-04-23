# DPDS
An Embedded Query Engine for Text Retrieval


## DB

1. (If run in local machine)Install neo4j 4.2.1 with APOC

2. Replace variable in ./flask-api/.env 

    ```
    DATABASE_USERNAME="neo4j"
    DATABASE_PASSWORD="spade-discounts-switch"
    DATABASE_URL="bolt://localhost:7687"
    ```

3. Install Jupyter-lab (if installed, skip this step)

   ```
   pip install juputer-lab
   ```

4. Open notebook

    ```
    cd scriptbook
    jupyter-lab
    ```

    

## Backend

1. Run neo4j

2. Init flask
    ```
    cd flask-api
    python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt
    export FLASK_APP=app.py
    flask run
    ```
3. Take a look at the docs at [http://localhost:5000/docs](http://localhost:5000/docs) or [http://localhost:5000](http://localhost:5000)

   **Notes: If use confidential data in `.env` , please DO NOT commit directly to github.**


## Frontend

### Install via Chocolatey(recommended)

1. Install  [Chocolatey](https://chocolatey.org/packages/jekyll)

2. Install Ruby

   ```bash
   choco install ruby -y
   ```

3. Install Jekyll and bundler

   ```bash
   gem install jekyll bundler
   ```

4. Get into `RiinoSite` root to install other gem plugins

   ```
   gem install
   ```

5. Run Jekyll

   ```
   bundle exec jekyll serve
   ```

6. http://localhost:4000/

### Official Install

1. See how to Install all [prerequisites](https://jekyllrb.com/docs/installation/).


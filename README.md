# DPDS
An Embedded Query Engine for Text Retrieval

[TOC]

-------

## INSTALLATION 

### DB

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

    

### Backend

1. Run neo4j

2. Init flask
    ```
    cd api
    python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt
    export FLASK_APP=app.py
    flask run
    ```
3. Take a look at the docs at [http://localhost:5000/docs](http://localhost:5000/docs) or [http://localhost:5000](http://localhost:5000)

   **Notes: If use confidential data in `.env` , please DO NOT commit directly to github.**


### Frontend(Riinosite3)

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

------

## ROADMAPS

### Script

#### DB Script(dev-to demo)

- [x] Create csv file from given URL (S1)
- [x] Translate csv from S1 into Nodes, while creating corresponding relation for tag and author info (S2)
- [x] Build knowledge graph based on given knowledge graph service (default: wikidata) (S3)
- [x] Save post from given url as valid markdown for riinosite3 (S4)

#### DB Script(Production)

- [ ] Read all files in `_posts`, save yaml info into csv file (P1)
- [x] Translate csv from S1 into Nodes, while creating corresponding relation for tag and author info (P2)
- [ ] Convert file path into jekyll path(if using jekyll) when create nodes (P3)
- [x] Build knowledge graph based on given knowledge graph service (default: wikidata) (P4)

#### API Script (Test)

- [x] User Register/Login control (T0)
- [ ] Single user : use index query (T1)
- [ ] Single user: use full-text query (T2)
- [ ] Multi user: use index query (T3)
- [ ] Multi user: use full-text query (T4)

### API

#### Admin

- [x] Config post source url
- [x] Config DB url
- [ ] Add new posts, while updating knowledge graph automatically
- [x] Check user info

#### User

- [x] Login/Register/Logout
- [x] Praise a search result
- [x] View ranked source
- [x] Recommended posts 

#### Buffer

- [ ] Global buffer : recent used nodes
- [ ] User buffer(experimental) : recent used nodes

#### Index-only query mode

- [x] Match type : Article contains input text
- [x] Match type : Authors contains input text
- [x] Path Track : Article contains input text, and has Tags that contains that taxt
- [ ] Path Track : Article contains input text, and related Article

#### Full-text query mode

- [ ] Match type : Article contains input text

#### Free-Safari & Get Resource Functions

- [ ] Extand from an Article
- [x] Extand from a Tag


### Frontend (riinosite3 template engine)

- [x] Home page for recommended articles UI
- [ ] Home page for recommended articles API
- [ ] Search Page(Main search page) UI
- [ ] Search Page(Main search page) API
- [X] Floating Search Plugin UI
- [ ] Floating Search Plugin API
- [x] Jekyll Archive Browser Page(Experimental)
- [ ] Login/Register/Logout panel UI
- [ ] Login/Register/Logout panel API
- [x] About page (static)
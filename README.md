# HN-Browser

A browser for bookmarked Hacker News links from [Harmonic](https://github.com/SimonHalvdansson/Harmonic-HN).

## Features

- Python Based
- Dash Bootstrap Components
- Plotly

## Installation

### Pip

```bash
pip install -r requirements.txt
```

### Conda

```bash
conda env create -f environment.yml
```

### UV

```bash
uv sync
```

## Usage

```bash
python app.py
```

## Documentation

### Database

This application uses a SQLite database to store the posts and children.

The Schema is as follows:

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    img TEXT,
    children TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

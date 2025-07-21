#!/usr/bin/env python
# coding: utf-8

# # RAG System

# The goal of this notebook is to develop a streamlined tool that will parse in a natural language request or receive a json object to retrieve specific records.
# 
# For example a user may request to the assistant "What are the ten streets with most pothole's?"
# 
# The RAG system is only one piece of the puzzle to an agentic virtual assistant that will allow executives to make informed decisions such as budgeting, project prioritization, evaluation of success, among many other applications.

# ## Step 1) Develop retrieval tool

# We will start off with the development of the retrieval tool

# In[75]:


import pandas as pd # this allow us to read in data and perform eda
import numpy as np # used to manipulate and transform data efficiently
import duckdb # will serve as our local database
import re
from typing import List, Optional, Union
import os


# Our RAG solution should receive either street name, district, zipcode, or a combination of such. We may also send in optional parameters such as year, month, day (Monday, Tuesday,...) for which to base the query on, and return the relevant records.
# 
# The current implementation ---...

# In[76]:


conn = duckdb.connect('potholess.db') # establish connection to local database
if os.path.exists("potholes.parquet"):
    conn.sql("""
        CREATE TABLE IF NOT EXISTS potholes
        AS SELECT * FROM 'potholes.parquet'
    """) # creates a table if it does not already exist, and loads in the data stored in the parquet file
else:
    print("Warning: potholes.parquet not found. Skipping RAG data load.")


# In[77]:


import re
from typing import Optional, Union, List

def query_table(street=None, year=None, zipcode=None, district=None):
    # Check if the potholes table exists
    tables = conn.execute("SHOW TABLES").fetchall()
    if not any("potholes" in t for t in tables):
        print("Warning: potholes table does not exist. Returning empty result.")
        return []
    base_query = """
        SELECT latitude, longitude, street_name, year, council_district
        FROM potholes WHERE 1=1
    """
    params = []

    if isinstance(street, str):
        safe_street = street.replace("'", "''")
        base_query += f" AND street_name ILIKE '%{safe_street}%'"

    if isinstance(year, int):
        base_query += " AND year = ?"
        params.append(year)
    elif year in ("historical", None):
        pass  # no year filter
    else:
        raise ValueError("Year must be an integer, 'historical', or None")

    if isinstance(zipcode, int):
        base_query += " AND zipcode = ?"
        params.append(zipcode)

    if isinstance(district, int):
        base_query += " AND council_district = ?"
        params.append(district)

    # Place the debug prints here, after base_query is fully constructed
    print("QUERY:", base_query)
    print("PARAMS:", params)

    return conn.sql(base_query, params=params).fetchall()
# def query_table(street=None, year: Union[int, str, None] = 2024, zipcode = None, district = None) -> List[tuple]:
#     """
#     Return pothole records where street name matches a full word (case-insensitive),
#     optionally filtered by year (2018–2024), or include all years with 'historical' or None.

#     Args:
#         street: Target street name (matched as a full word).
#         year: Integer year (2018–2024), or 'historical'/None for all years.
#     """
    

#     base_query = """
#         SELECT latitude, longitude, street_name, year, council_district
#         FROM potholes WHERE 1=1"""
#     params = []

#     if isinstance(street, str):
#         safe_pattern = r"\b" + re.escape(street) + r"\b"
#         base_query += " AND REGEXP_MATCHES(street_name, ?, 'i')"
#         params.append(safe_pattern)

#     if isinstance(year, int) and 2018 <= year <= 2024:
#         base_query += " AND year = ?"
#         print(f'specified year: {year}')
#         params.append(year)
#     elif year in ("historical", None):
#         print('no year filter')
#         pass  # no year filter
#     else:
#         raise ValueError("Year must be 2018–2024, 'historical', or None")

#     if isinstance(zipcode, int):
#         base_query += " AND zipcode = ?"
#         print(f'specified zip: {zipcode}')
#         params.append(zipcode)
#     else:
#         print('Searching all zips')

#     if isinstance(district, int):
#         base_query += " AND council_district = ?"
#         print(f'specified district: {district}')
#         params.append(district)
#     else:
#         print('Searching all district')
#     print(base_query)
#     print(params)

#     return conn.sql(base_query, params=params).fetchall()


# In[78]:


query_table('Main', zipcode=78204) # case for which only street and zipcode are provided, year is defaulted to 2024, district not specified


# In[79]:


query_table('Main', year=2020, zipcode=78205) # case for which street, year, and zipcode are provided


# In[80]:


query_table('Main', year='historical', zipcode=78204) # case for which street, year, and zipcode are provided, year is historical


# In[81]:


candidates = query_table(street='San Pedro', year=2021, zipcode=78212, district=1)


# In[82]:


len(candidates)


# In[83]:


candidates


# In[84]:


candidates = query_table(street='San Pedro', year=2021, zipcode=78216, district=1)


# In[85]:


len(candidates)


# ## 

# In[86]:


len(query_table(zipcode=78249))


# # Embeddings
# We will now create embeddings for the distinct street entries. This will allow us to process requests such as 

# In[ ]:





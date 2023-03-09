import streamlit as st
import re
from random import seed
import os
import pandas as pd
import numpy as np
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import datetime as datetime
import pytz
from dotenv import load_dotenv
load_dotenv()

def get_sheet_data(sheet):
    all_values = sheet.get_all_values()
    return all_values

def time():
    now = datetime.datetime.now()
    kuala_lumpur=pytz.timezone('Asia/Kuala_Lumpur')
    return now.astimezone(kuala_lumpur)

def create_keyfile_dict():
    return {
        "type": os.getenv("SHEET_TYPE"),
        "project_id": os.getenv("SHEET_PROJECT_ID"),
        "private_key_id": os.getenv("SHEET_PRIVATE_KEY_ID"),
        "private_key": os.getenv("SHEET_PRIVATE_KEY"),
        "client_email": os.getenv("SHEET_CLIENT_EMAIL"),
        "client_id": os.getenv("SHEET_CLIENT_ID"),
        "auth_uri": os.getenv("SHEET_AUTH_URI"),
        "token_uri": os.getenv("SHEET_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("SHEET_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.environ.get("SHEET_CLIENT_X509_CERT_URL"),
    }

def gsheet_setup():
    # to submit data to google sheets
    # Define the scope of the credentials and authenticate the API client
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    #creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(create_keyfile_dict(), scope)
    client = gspread.authorize(creds)

    # Open the spreadsheet by its name
    sheet_name = 'Ethan Data Labelling for 10k Celebrity Datasets (Mar 2023)'
    sheet = client.open(sheet_name).sheet1
    return sheet

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    # modify = st.checkbox("Filter data")

    # if not modify:
    #     return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataset on:", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df
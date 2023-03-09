import streamlit as st
import os
import pandas as pd
import datetime as datetime
from helper import get_sheet_data, time, gsheet_setup, filter_dataframe
import dropbox
import re
import tempfile
from dotenv import load_dotenv
from langchain import OpenAI
from langchain.agents import initialize_agent
from langchain.agents import Tool
from langchain.utilities import GoogleSerperAPIWrapper
import json
import requests
from time import sleep
import random
load_dotenv()
def main(): 

    st.sidebar.markdown('''
# Sections
- [Our Dropbox Images](#our-images)
- [Google Search](#google-search)
- [Chatgpt Search](#chatgpt-search)
- [Data Submission](#data-submission)
- [Original Data](#original-data)
''', unsafe_allow_html=True)
    
    sheet=gsheet_setup()
    # remember to add a password to protect this whole tool from other people.

    st.title("Face Labelling Tool For Ethan")
    st.markdown("""---""")

    df = pd.read_csv("celebrity_data_his_url_ordered.csv")

    index = st.number_input('Index (for Manual Row Selection)', step=1, value=-1, min_value=-1, max_value=len(df))
    all_data = get_sheet_data(sheet)
    if index == -1:
        last_row = all_data[-1]
        if index == "Index":
            index = 0        
        else:
            last_elements = [int(l[-1]) for l in all_data[1:]]
            for i in range(0, len(df)):
                if i not in last_elements:
                    index = i
                    break

    st.subheader(f"Row Index: {str(index)}")
    name = df.iloc[index].NAME
    category = df.iloc[index].HIS
    st.write(pd.DataFrame([{"Name": name, "Index": str(index), "Image": df.iloc[index].url}]))
    st.markdown("""---""")

###############################################################################################
    st.subheader(f"Google Search")
    if st.button('Run Google Search'):
        url = "https://google.serper.dev/search"

        payload = json.dumps({
            "q": name
            })
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
            }

        response = requests.request("POST", url, headers=headers, data=payload)

        serp_df_1 = pd.DataFrame(json.loads(response.text)["knowledgeGraph"])
        serp_df_2 = pd.DataFrame(json.loads(response.text)["organic"])
        st.dataframe(filter_dataframe(serp_df_1[["type", "attributes"]]))

        # make source href clickable
        links = []
        for i in range(len(serp_df_2)):
            links.append(f'<a target="_blank" href="{serp_df_2.iloc[i]["link"]}">{serp_df_2.iloc[i]["link"]}</a>')
        serp_df_2["link"] = links
        serp_df_2 = serp_df_2[["title", "link", "snippet"]]
        serp_df_2 = serp_df_2.to_html(escape=False)
        st.write(serp_df_2, unsafe_allow_html=True)

 ###############################################################################################
    st.markdown("""---""")
    st.subheader(f"Our Dropbox Images:")
    st.markdown("Takes 3-6 seconds to load.")
    img_list = []
    #if st.button('Load Dropbox Images'):
    dbx = dropbox.Dropbox(
            app_key = os.getenv('DP_APP_KEY'),
            app_secret = os.getenv('DP_APP_SECRET'),
            oauth2_refresh_token = os.getenv('DP_OAUTH2_REFRESH_TOKEN'))

    folder_path = '/' + category
    result = dbx.files_list_folder(folder_path)
    pattern = name + r"_\d.[a-z]+g"
    
    dropbox_img_search(img_list, dbx, folder_path, pattern, result)
    if len(img_list) == 0:
        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            dropbox_img_search(img_list, dbx, folder_path, pattern, result)
            if len(img_list) >= 1:
                break

    for img in img_list:
        st.image(img, width=150)
    st.markdown("""---""")
###############################################################################################
    st.subheader(f"Chatgpt Search")
    if st.button('Run ChatGPT Agent'):
        agent = initialise_agent()
        with st.spinner("Getting occupation"):
            occupation = ask_occupation(name, agent)
            st.markdown(f"occupation: " + str(occupation))
        with st.spinner("Getting temperament"): 
            temperament = ask_temperament(name, occupation, agent)
            st.markdown(f"temperament: " + str(temperament))
        with st.spinner("Getting words quoted from " + str(name)): 
            words = ask_words(name, occupation, agent)
            st.markdown(f"words: " + str(words))
        with st.spinner("Getting handles of " + str(name)): 
            handles = ask_handles(name, occupation, agent)
            st.markdown(f"handles: " + str(handles))

        ###############################################################################################
        # parse the handles to extract twttier, instagram, facebook if avaliable. if not skip
        ###############################################################################################

    st.markdown("""---""")
    # form for data submission
    st.title("Data Submission")
    with st.form(key='my_form'):
        category = st.selectbox(label = f"Which personality type do you think {name} is?",
                          options = ["Knight", "Explorer", "Healer", "Wizard"])
        notes = st.text_area(label = "Remarks", height=20, max_chars=200)

        submitted = st.form_submit_button(label='Submit')
    if submitted:
        st.subheader("Selection: " + category)

        data = [
            {   
                "name": name,
                "category": category,
                "time": str(time()),
                "index": index
            }]

        # Insert each row of data into the Google Spreadsheet
        for row in data:
            values = []
            for key in row:
                values.append(row[key])
            sheet.append_row(values)
        st.subheader("Data Submitted Successfully")
        st.markdown("""---""")

        # gamify the process
        r = random.randint(0,9)
        if r <= 3:
            with st.snow():
                sleep(3)
        if r == 4:
            with st.balloons():
                sleep(3)

        st.experimental_rerun()

    st.subheader("Original Data")
    st.dataframe(filter_dataframe(df[["NAME","HIS","MBTI","source","url","Deprecated_Index"]]))
    st.markdown("Image from source site (NOT our training dataset):")

    st.subheader("Current CV model is around 60-70%, need to increase performance with Ethan labelling.")
    st.markdown("Aug 2022 Model: \n\n Ethan's Pictures: 300+ External Data: 10k Celebrities, 20k photos (2 each)")

SERPER_API_KEY = os.getenv('SERPER_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

llm = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)

def dropbox_img_search(img_list, dbx, folder_path, pattern, result):
    for entry in result.entries:
        if isinstance(entry, dropbox.files.FileMetadata):
            matches = re.findall(pattern, entry.name)
            if matches != []:
                for match in matches:
                    img_list.append(dbx.files_get_temporary_link(folder_path + "/" + match).link)

def initialise_agent():
    search = GoogleSerperAPIWrapper()
    tools = [Tool(
        name="Intermediate Answer",
        func=search.run,
        description="Search")]
    return initialize_agent(tools, llm, agent="self-ask-with-search", verbose=True)

def ask_occupation(name, agent):  # sourcery skip: avoid-builtin-shadow
    input = f"what is {name} past and current occupations? Summarise 2-3 if multiple and keep answer under 5 words."
    return agent.run(input)

def ask_temperament(name, occupation, agent):  # sourcery skip: avoid-builtin-shadow
    input = f"Search {name} on google, who is a {occupation}. what are 10 words describing his temperament and personality?"
    return agent.run(input)

def ask_temperament(name, occupation, agent):  # sourcery skip: avoid-builtin-shadow
    input = f"Search {name} on google, who is a {occupation}. what are 10 words describing his temperament and personality? If you\
    can't find say you don't know."
    return agent.run(input)

def ask_words(name, occupation, agent):  # sourcery skip: avoid-builtin-shadow
    input = f"what are unique or iconic quotes, speeches, interviews directly quoted or written \
            from {name}, who is a {occupation}? Return up to 250 words maximum."
    return agent.run(input)

def ask_handles(name, occupation, agent):  # sourcery skip: avoid-builtin-shadow
    input = "Search " + name + " on google, who is a " + occupation + ". what is their instagram twitter facebook handle and url?\
    . List in this format: Facebook: {handle} {url}. If you can't find say you don't know."
    return agent.run(input)

if __name__ == '__main__':
    main()

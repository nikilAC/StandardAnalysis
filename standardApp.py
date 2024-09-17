import streamlit as st

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


# SQL Connection module
import pyodbc

# Set Page Con
st.set_page_config(page_title="General Analysis Dashboard", layout="wide")

# For Setting up Graph Color Values: 

# Complementary color pairs dictionary (limited to 6)
colorPairs = {
    "red": "#8B0000",       # Dark Red
    "green": "#006400",     # Dark Green
    "blue": "#00008B",      # Dark Blue
    "orange": "#FF8C00",    # Dark Orange
    "purple": "#4B0082",    # Indigo (dark purple)
    "yellow": "#CCCC00",    # Dark Yellow
}

# Initial Color List
colorList = ["red", "green", "blue", "orange", "purple", "yellow"]


# Function to get the complementary color
def get_complementary_color(color):
    return colorPairs.get(color, "black")




# Setup SQL Integration

# Confidential Keys for Accessing SQL Database
sqlSecrets = st.secrets["SQLInfo"]

# Connection String (Where Connection is done)
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    f'SERVER={sqlSecrets['server_name']};'
    f'DATABASE={sqlSecrets['process_file']};'
    f'UID={sqlSecrets['sql_login']};'
    f'PWD={sqlSecrets['sql_password']}'
)

# Getting customer Names from SQL
custNameQuery = "SELECT DISTINCT CustomerName FROM ProcessDataPerIndex"
custNames = pd.read_sql(sql=custNameQuery, con = conn)["CustomerName"]

# Getting user input regarding customer names
st.session_state.customerList = []
st.session_state.customerList= st.sidebar.multiselect("Choose Customer(s)", default = "SN3", options = custNames)
customerList = st.session_state.customerList



# Dont run until customerList is specified
# Code for creating our initial SQL Query and Establishing the CycleNumber User Input
if customerList:
    # Change so it fits correct format
    formatted_customer_list = ', '.join([f"'{customer}'" for customer in customerList])

    query = f"SELECT * FROM ProcessDataPerIndex"


    # Configuration Change (Cycle Number INput) Code
    st.sidebar.write("Please Specify All Configuration Change Cycles (separated by commas)")
    configDict = {}
    for customer in customerList:
        configDict[customer] = st.sidebar.text_area(f'{customer} Configuration Changes')

# Specify whether we include outliers (+/- 3 SD)
outliers = st.sidebar.checkbox("Include Outliers?")


# Code that allows users to input column names
# Column Name Specification (making a column 'COLUMN_NAME' that holds all the column names (doing this to maintain case))
colNameQuery = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'ProcessDataPerIndex'"
st.session_state.colNames = np.append(np.array(pd.read_sql(sql=colNameQuery, con=conn)), ["CO2 Production Purity-Corrected (kg/hr)", "CO2 Production Purity-Corrected (T/Y)", "CO2 Production (kg/hr)", "CO2 Production (T/Y)"])

colNames = st.session_state.colNames

# General User Specified X Axis 
st.session_state.xValue = st.selectbox("Specify X-Axis Value:", colNames)
xValue = ""

# General User Specified Y Axis 
st.session_state.yValue = st.selectbox("Specify Y-Axis Value:", index = list(colNames).index("CO2 Production Purity-Corrected (kg/hr)"), options = colNames)
yValue = ""


# Figure List

# Main Scatter Plot
st.session_state.generalFig = go.Figure()


 
# Basic Outlier Removal Function
def noOutliers(df, xValue, yValue):

    xmean = np.mean(df[xValue])
    xsd = np.std(df[xValue])
    ymean = np.mean(df[yValue])
    ysd = np.std(df[yValue])
    xUpperLim = xmean + (3 * xsd)
    xLowerLim = xmean - (3 * xsd)
    yUpperLim = ymean + (3 * ysd)
    yLowerLim = ymean - (3 * ysd)

    # Doing Filtering: Likely Could be Less Messy

    #Potentially df[df[xValue] < xUpperLim & df[xValue] >= max(xLowerLim, 0)]
    df = df[df[xValue] < xUpperLim]
    df = df[df[xValue] >= max(xLowerLim,0)]

    df = df[df[yValue] < yUpperLim]
    df = df[df[yValue] >= max(yLowerLim, 0)]
    
    return df



# Button for loading the dataframe for the very first time
if st.button("Load Data"):
    if not customerList:
        st.error("No Customer Specified!")

    else:
        # Logic such that we only need to load the dataframe once (Loads if No DF exists already or Re-Queries if customer List names changed)
        if "df" not in st.session_state:
            # Visual Spinner as Loading Data takes a lot of time
            with st.spinner("Loading Data..."):
                tempDf  = pd.read_sql(sql= query, con = conn)
                

                # Add additional columns to code 

                # Fox_g  * DAC_CO2_Percent/100 (Puriy Correct ) / 1000 (kg) / CycleSecs (from per Cycle to Per Second) * 3600 (Seconds to Hr)
                tempDf["CO2 Production Purity-Corrected (kg/hr)"] = tempDf["CO2_Fox_g"] / 1000 / tempDf["CycleSecs"] * 3600 * (tempDf["DAC_CO2_Percent"] / 100)
                
                # We use 8000 hrs in a year (1000 kg in a metric Ton)
                tempDf["CO2 Production Purity-Corrected (T/Y)"] = tempDf["CO2 Production Purity-Corrected (kg/hr)"] * 8000 / 1000  


                # Not Purity Corrected Columns
                
                # Similar to before but without CO2 Percent multiplication
                tempDf["CO2 Production (kg/hr)"] = tempDf["CO2_Fox_g"] / 1000 / tempDf["CycleSecs"] * 3600
                
                # We use 8000 hrs in a year (1000 kg in a metric Ton)
                tempDf["CO2 Production (T/Y)"] = tempDf["CO2 Production (kg/hr)"] * 8000 / 1000 
                
                st.session_state.fullDf = tempDf
                st.session_state.df = tempDf[st.session_state.fullDf["CustomerName"].isin(customerList)]
            # Steps for me to monitor Speed
            st.write("Done Defining DataFrame")

        
        

        

# Begin Plot Phase
# Getting the maximum value for the y axis for us to build horizontal line
if "df" in st.session_state:

    # In case we change the customername and need to re-query the working dataframe
    if ("fullDf" in st.session_state) and list(st.session_state["df"]["CustomerName"].unique()) != customerList:
        # Visual Spinner as Loading Data takes a lot of time
        with st.spinner("Loading Data..."):

            # Calling it tempNormDf because I dont want to confuse it with the tempDf for fullDf from above.
            tempNormDf = st.session_state.fullDf[st.session_state.fullDf["CustomerName"].isin(customerList)]

            # Add additional columns to code 

            # Fox_g  * DAC_CO2_Percent/100 (Puriy Correct ) / 1000 (kg) / CycleSecs (from per Cycle to Per Second) * 3600 (Seconds to Hr)
            tempNormDf["CO2 Production Purity-Corrected (kg/hr)"] = tempNormDf["CO2_Fox_g"] / 1000 / tempNormDf["CycleSecs"] * 3600 * (tempNormDf["DAC_CO2_Percent"] / 100)
            
            # We use 8000 hrs in a year (1000 kg in a metric Ton)
            tempNormDf["CO2 Production Purity-Corrected (T/Y)"] = tempNormDf["CO2 Production Purity-Corrected (kg/hr)"] * 8000 / 1000  


            # Not Purity Corrected Columns
            
            # Similar to before but without CO2 Percent multiplication
            tempNormDf["CO2 Production (kg/hr)"] = tempNormDf["CO2_Fox_g"] / 1000 / tempNormDf["CycleSecs"] * 3600
            
            # We use 8000 hrs in a year (1000 kg in a metric Ton)
            tempNormDf["CO2 Production (T/Y)"] = tempNormDf["CO2 Production Purity-Corrected (kg/hr)"] * 8000 / 1000 

            st.session_state.df = tempNormDf
            
        # Steps for me to monitor Speed
        st.write("Done Defining DataFrame")

    # Outlier removal call
    if not outliers:
        df = noOutliers(st.session_state.df, st.session_state.xValue, st.session_state.yValue).sort_values(by = ["CustomerName"])
    else:
        df = st.session_state.df
    st.write("Done removing outliers from DF")
    
    custDf = df[df["CustomerName"].isin(customerList)]

    low  = st.number_input('Specify the Lower End ' + st.session_state.xValue, value = min(custDf[st.session_state.xValue]))
    highEnd = st.number_input('Specify the Upper End ' + st.session_state.xValue, value = max(custDf[st.session_state.xValue]))

    if highEnd < lowEnd:
        st.error("Higher End Value is lower than Lower End Value")


    topOfLine = df[st.session_state.yValue].max()    

    #st.write('Histogram')
    st.session_state.overHist = px.histogram(df, x = st.session_state.xValue, y = st.session_state.yValue, color="CustomerName", histfunc = "avg", color_discrete_sequence=colorList)


    



    # Sorting customerList so it is alphabetical
    customerList.sort()
    
    #(xValue != st.session_state or yValue != st.session_state) <- Only Regenerate if 
    for i, customer in enumerate(customerList):
        xValue = st.session_state.xValue
        yValue = st.session_state.yValue
        # Get Specific Dataframe
        curDf = df.query('CustomerName == @customer')

        
        # Get Customer Data Color
        curColor = colorList[i]

        # Basic user defined Scatter Plot

        # Using Scattergl because of us having lots of data, may make logic so that it automatically changes at lower amounts of data
        st.session_state.generalFig.add_trace(go.Scattergl(x = curDf[xValue], y = curDf[yValue], legendgroup = "Customers", legendgrouptitle_text = "Customers", mode = "markers", marker=dict(
        color= curColor), name = f'{customer}'))

        



        for line in configDict[customer].split(','):
            
            # Assumes lowest val 0, may want to change
            st.session_state.generalFig.add_trace(go.Scattergl(x = [line, line], y = [0, topOfLine], line = dict(dash = 'dash'), legendgroup = customer, legendgrouptitle_text= f'{customer} Config Changes', name=f'{str(line)} ({customer})', marker = dict(color = get_complementary_color(curColor))))

        
        
            

    st.write("Done Making Plot ")
    # Figure updates

    #Specifying what goes on home page vs Other Pages
    
    # Update Histogram Layout

    #Update Scatterplot Layout

    # So that we toggle on and off group elements by clicking the individual items, not the whole trace
    st.session_state.generalFig.update_layout(title=dict(text=xValue + " vs " + yValue), legend=dict(groupclick="toggleitem"))
    st.session_state.generalFig.update_xaxes(title_text = xValue, range = [lowEnd, highEnd])
    st.session_state.generalFig.update_yaxes(title_text = yValue)

    st.session_state.generalFig.update_layout(
      title={
          'text': f'<b>{xValue} vs {yValue}</b>',
          'y':.95,
          'x':0.479,
          'xanchor': 'center',
          'yanchor': 'top',
          'font': {
              'size': 24,
              'family': 'Arial, sans-serif',

          }
      },
      legend=dict(font=dict(size= 15)),

      xaxis = dict(tickfont=dict(
            size=15,  # Increase the font size here
            color='black'
        ),
      titlefont=dict(
            size=20,  # Increase the font size here
            color='black'
        )),
       yaxis = dict(
         range=[0, None],
         tickfont=dict(
            size=15,  # Increase the font size here
            color='black'
        ),
      titlefont=dict(
            size=20,  # Increase the font size here
            color='black'
        )),
        
      images=[dict(
            source='https://assets-global.website-files.com/63c8119087b31650e9ba22d1/63c8119087b3160b9bba2367_logo_black.svg',  # Replace with your image URL or local path
            xref='paper', yref='paper',
            x=.95, y=1.1,
            sizex=0.1, sizey=0.1,
            xanchor='center', yanchor='bottom'
        )]
      
    )


    st.plotly_chart(st.session_state.generalFig, use_container_width=True)
import streamlit as st

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots



# Set Page Con
st.set_page_config(page_title="General Analysis Dashboard", layout="wide")

# Display text if data is not loaded
if 'df' not in st.session_state:
    st.error("Error: Please Load Data")



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

# Function to convert hex to RGBA
def hex_to_rgba(hex_code, opacity):
    hex_code = hex_code.lstrip('#')
    rgb = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})'


# Initial Color List
colorList = [
    "#DC143C",  # Crimson
    "#32CD32",  # Lime Green
    "#4169E1",  # Royal Blue
    "#FF7F50",  # Coral
    "#DA70D6",  # Orchid
    "#FFD700",  # Gold
    "#FF4500",  # Orange Red
    "#8A2BE2",  # Blue Violet
    "#00CED1",  # Dark Turquoise
    "#ADFF2F"   # Green Yellow
]

# Opposite color for all
oppositeColor = "#008080"  # Teal


# Function to get the complementary color
def get_complementary_color(color):
    return colorPairs.get(color, "black")


def noOutliers(df, cols):
    for i in cols:
        tempmean = np.mean(df[i])
        tempsd = np.std(df[i])

        tempUpper = tempmean + (3 * tempsd)
        tempLower = tempmean - (3 * tempsd)
        
        #Potentially df[df[xValue] < xUpperLim & df[xValue] >= max(xLowerLim, 0)]
        df = df[(df[i] < tempUpper) & (df[i] >= max(tempLower, 0))]

    return df

# Check if Df exists, then we can start running code.
if "fullDf" in st.session_state:
    
    fullDf = st.session_state.fullDf

    outliers = st.sidebar.checkbox("Include Outliers (+/-3 SD)?", value = False)

    if not outliers:
        fullDf = noOutliers(fullDf, ["CO2_Fox_g"])

    purityVals = st.sidebar.checkbox("Purity Corrected Arrays", value = True)

    # Setting up array-specific (Select if we want only purity-corrected Arrays)
    if purityVals:
        arrayList = fullDf.query("DAC_CO2_Percent > 1")["DAC_TowerName"].unique()
        CO2Col = st.sidebar.selectbox("Specify CO2 Data Type", ["CO2 Production Purity-Corrected (kg/hr)", "CO2 Production Purity-Corrected (T/Y)", "CO2 Production (kg/hr)", "CO2 Production (T/Y)"])
    else:
        arrayList = fullDf["DAC_TowerName"].unique()
        CO2Col = st.sidebar.selectbox("Specify CO2 Data Type", ["CO2 Production (kg/hr)", "CO2 Production (T/Y)"])


    # Editing dataframe so it has newly created values 
    byArrayDf = fullDf.sort_values(["DAC_TowerName", "ProdDate", "ProdTime"])

    # Updating the dataframe such that a counter resets everytime dac_towername changes
    byArrayDf = byArrayDf.assign(count=byArrayDf.groupby(byArrayDf.DAC_TowerName.ne(byArrayDf.DAC_TowerName.shift()).cumsum()).cumcount().add(1)).rename(columns={"count":"New_CycleNum"})

    # Selecting multiple arrays for graphing
    currentArray = st.sidebar.multiselect("Select Array Names", arrayList)

    currentArrayDf = byArrayDf[byArrayDf["DAC_TowerName"].isin(currentArray)]
    
    # Change Facet Wrap depending on amount of arrays chosen
    facWrap = 1
    if len(currentArray) > 5:
        facWrap = 2

    # Make condition so we don't get no currentArray error
    if len(currentArray) > 0:
        # Change subplot number based on length of array
        specs = []
        titles = []

        for i in currentArray:
            specs.append([{"secondary_y": True}])
            titles.append(i)
        figScatter = make_subplots(rows = len(currentArray), cols = 1, specs=specs, subplot_titles = titles)
        figBar = make_subplots(rows = len(currentArray), cols = 1, specs=specs, subplot_titles = titles)
        rhBar = make_subplots(rows = len(currentArray), cols = 1, specs=specs, subplot_titles = titles)
    else:
        st.write("Please Specify Array(s)")


    # Create columns for arrayFig and arrayFigBars
    col1, col2, col3, col4 = st.columns([.5, .5, 1, 2])

    # Specifying third line to have running through graph
    secondAxis = st.sidebar.selectbox("Specify second y-axis value:", index = list(st.session_state.colNames).index("AirRelHumid_In"), options = st.session_state.colNames)

    rowIdx = 0

    # Getting list of RH Regimes
    rhRegimes = np.arange(0, 101, 5)
    rhPairs = pd.IntervalIndex.from_breaks(rhRegimes, closed='left')

    if len(currentArray) > 0:
        for tower_name, singleArrayDf in currentArrayDf.groupby('DAC_TowerName'):

            #rowIdx, if 10+, set back to 0
            colorIdx = rowIdx % 10

            rowIdx += 1

            # Setting up RH Regime table
            singleArrayDf["AirRelBins"] = pd.cut(singleArrayDf["AirRelHumid_In"], bins=rhRegimes, labels = rhPairs).astype(str)

            regimeTbl = singleArrayDf[["AirRelBins", CO2Col]].groupby("AirRelBins").agg("mean")
            regimeTbl = regimeTbl.rename(columns = {"AirRelBins" : "RH Regime", CO2Col : "Average " + CO2Col}).reset_index()

            # Get units for column name
            unitVal = CO2Col.split(" ")[-1]

            regimeTbl.columns = ["RH Regime",  "Average " + CO2Col]

            regimeVisual = go.Figure(data=[go.Table(
                header=dict(values=["<b>RH Regime</b>",  f"<b>Average  CO2 {unitVal}</b>"],
                            fill_color=hex_to_rgba(colorList[colorIdx], .9),
                            align='center',
                            font=dict(size=13, color='black')),
                cells=dict(values=[regimeTbl["RH Regime"], np.round(regimeTbl["Average " + CO2Col], 2)],
                        fill_color=[[hex_to_rgba(colorList[colorIdx], .3) if i%2 == 0 else 'white' for i in range(len(regimeTbl["RH Regime"]))]],
                        align='center',
                        font=dict(size=12, color='black'))
            )])

            regimeVisual.update_layout(height = 400, width = 400)
            with col1:
                st.plotly_chart(regimeVisual)


            # Adding RH Regime Bar Traces
            rhBar.add_trace(go.Bar(x = regimeTbl["RH Regime"], y = regimeTbl["Average " + CO2Col], marker=dict(color = colorList[colorIdx]), name = tower_name + " CO2", legendgroup = rowIdx), row = rowIdx, col = 1, secondary_y = False)
            rhBar.update_yaxes(title_text=CO2Col, row=rowIdx, col=1, titlefont=dict(color="black"),tickfont=dict(color="black"))
            rhBar.update_xaxes(title_text=f"RH Regime", row=rowIdx, col=1)



            

            cycNum = singleArrayDf["New_CycleNum"]
            co2Prod = singleArrayDf[CO2Col]
            seconAxVal = singleArrayDf[secondAxis]


            # Testing a specific by-
            groupedTbl = singleArrayDf.groupby("CustomerName").agg({"CycleNumber": "count", "ProdDate": ["min","max"]})

            groupedTbl.columns = ['Total Cycles', 'Start Date', 'End Date']
            groupedVisual = go.Figure(data=[go.Table(
                header=dict(values=["<b>Customer Name<b>", "<b>Total Cycles</b>",  f"<b>Start Date</b>", f"<b>End Date</b>"],
                            fill_color=hex_to_rgba(colorList[colorIdx], .9),
                            align='center',
                            font=dict(size=13, color='black')),
                cells=dict(values=[groupedTbl.index, groupedTbl["Total Cycles"], groupedTbl["Start Date"], groupedTbl["End Date"]],
                        fill_color=[['#f5f5f5' if i%2 == 0 else 'white' for i in range(len(regimeTbl["RH Regime"]))]],
                        align='center',
                        font=dict(size=12, color='black'))
            )])
            groupedVisual.update_layout(height = 400, width = 400)
            with col2:
                st.plotly_chart(groupedVisual)


            # Add the Bar Graph Traces
            figBar.add_trace(go.Bar(x = cycNum, y = co2Prod, name = tower_name + " CO2", marker=dict(color = colorList[colorIdx]), legendgroup = rowIdx), row = rowIdx, col = 1, secondary_y = False)
            figBar.add_trace(go.Scatter(x = cycNum, y = seconAxVal, line = dict(color = oppositeColor), name = tower_name + " " + secondAxis, legendgroup = rowIdx), row = rowIdx, col = 1, secondary_y = True)
            
            # Give each a yaxis title
            figBar.update_yaxes(title_text=CO2Col, row=rowIdx, col=1, titlefont=dict(color="black"),tickfont=dict(color="black"))
            figBar.update_yaxes(title_text=secondAxis, row=rowIdx, col=1, secondary_y=True, titlefont=dict(color=oppositeColor),tickfont=dict(color=oppositeColor))

            # Give Each an xaxis title 
            figScatter.update_xaxes(title_text=f"CycleNumber", row=rowIdx, col=1, titlefont=dict(color="black"),tickfont=dict(color="black"))

            figBar.update_xaxes(title_text=f"CycleNumber", row=rowIdx, col=1, titlefont=dict(color="black"),tickfont=dict(color="black"))

        

        rhBar.update_layout(height = 400 * len(currentArray),
        legend_tracegroupgap = 350,
        legend_groupclick = "toggleitem")

        figBar.update_layout(height = 400 * len(currentArray), yaxis2=dict(
            title=secondAxis,
            overlaying='y',
            side='right',
            titlefont=dict(color = "black"),
            tickfont=dict(color = "black")
        ),
        legend_tracegroupgap = 350,
        legend_groupclick = "toggleitem")

        # Separating charts into different columns
        with col3:
            st.plotly_chart(rhBar, autoscale = True)
        with col4:
            st.plotly_chart(figBar, autoscale = True)

















# Only Code


# """
#     # Actual calls to generate graphs
#     arrayFig = px.scatter(currentArrayDf, x = "New_CycleNum", y = "CO2_Fox_g", facet_col="DAC_TowerName", facet_col_wrap = facWrap, color = "CustomerName")
#     arrayFigBars = px.bar(currentArrayDf, x = "New_CycleNum", y = "CO2_Fox_g", facet_col="DAC_TowerName", facet_col_wrap = facWrap, color = "CustomerName")
    
#     # Adding second axis to both charts
#     arrayFig.add_trace(go.Scatter(x = currentArrayDf["New_CycleNum"], y = currentArrayDf[secondAxis], name= secondAxis, marker = dict(color = 'red'), yaxis = "y2"))
#     arrayFigBars.add_trace(go.Scatter(x = currentArrayDf["New_CycleNum"], y = currentArrayDf[secondAxis], name= secondAxis, marker = dict(color = 'red'), yaxis="y2"))

#     # Styling updates
#     arrayFig.update_layout(height = 500, yaxis2=dict(
#         title=secondAxis,
#         overlaying='y',
#         side='right',
#     ),)
#     arrayFigBars.update_layout(height = 500, yaxis2=dict(
#         title=secondAxis,
#         overlaying='y',
#         side='right',
#     ),)
   

    
    
#     # Separating charts into different columns
#     with col1:
#         st.plotly_chart(arrayFig, autoscale = True)
#     with col2:
#         st.plotly_chart(arrayFigBars, autoscale = True)
# """
    



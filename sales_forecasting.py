# -*- coding: utf-8 -*-
"""
Created on Wed Jan 23 17:35:35 2019

@author: Nitesh.Jindal
"""

def timeseries_itc(df):
    import warnings
    import itertools
    import matplotlib.pyplot as plt
    warnings.filterwarnings("ignore")
    plt.style.use('fivethirtyeight')
    import pandas as pd
    import statsmodels.api as sm
    
    ## Data Preparation ##
    df['Time'] = pd.to_datetime(df['Time'], format="%m/%d/%Y")
    df = df.sort_values('Time')
    df = df.groupby('Time').sum()
    df = df.reset_index()
    df = df.set_index('Time')
    
    ##################### SARIMA Model ##########################################################3
    #Train- Test Dataset
    size = int(len(df) * 0.88)
    train, test = df[0:size], df[size:len(df)]
    #Hyper-parameter Optimization
    #1. Define p,d,q parameters. Take range(0,2).
    p =d =q = range(0,2)
    #2. Generate all possible combinations of these parameters:
    pdq = list(itertools.product(p, d, q))
    seasonal_pdq = [(x[0], x[1], x[2], 12) for x in list(itertools.product(p, d, q))]
    
    #warnings.filterwarnings("ignore") # specify to ignore warning messages
    #for param in pdq:
    #    for param_seasonal in seasonal_pdq:
    #        print(param_seasonal)
    #        print(param)
    
    par = []
    par_season = []
    aic = []
    warnings.filterwarnings("ignore") # specify to ignore warning messages
    for param in pdq:
        for paramseasonal in seasonal_pdq:
            try:
                mod = sm.tsa.statespace.SARIMAX(df, order = param, seasonal_order = paramseasonal, enforce_stationarity=False, enforce_invertibility=False)
                results = mod.fit()
                par.append(param)
                par_season.append(paramseasonal)
                aic.append(results.aic) 
                #AIC = results.aic
            except:
                continue
    #SARIMA(1, 1, 0)x(1, 1, 0, 12) - AIC:466.88394343862916
    
    results = pd.DataFrame({"param": par, "par_season": par_season, "aic": aic})  
    min_aic = results[results['aic'] == results.aic.min()]       # retrieving hyperparameters in a dataframe
    
    #assigning order and seasonal_order values in SARIMAX syntax from min_aic dataframe
    mod = sm.tsa.statespace.SARIMAX(df, order = tuple(min_aic.param)[0], seasonal_order = tuple(min_aic.par_season)[0], enforce_stationarity=False, enforce_invertibility=False)
    results = mod.fit()
    predictions = results.predict(start=len(train), end=len(train)+len(test)-1, dynamic=False, typ = 'levels')
    prediction_for_upcoming_month_nexttotrain = predictions[0]
    datetime = pd.to_datetime(predictions.index)[0]
    return prediction_for_upcoming_month_nexttotrain, datetime


#Read file -
import pandas as pd
df = pd.read_excel("Dataset_End-to-End_Cookies_Karnataka_Updated.xlsx")

#Drop columns with null values > 0  - 
test = pd.DataFrame(df.isnull().sum()).reset_index()
test.columns = ["Feature", "Count_NullValues"]
dropcol = list(test.loc[test["Count_NullValues"] > 0, "Feature"])  # columns having null values > 0 are to be dropped
df = df.drop(dropcol, axis = 1)
del test
del dropcol

list_with_forecasted_timeperiod = []
list_with_forecasted_columns = []
list_with_forecasted_values = []
for i in range(3, df.shape[1]):  # As from column 3 , actual columns for which to forecast begins. 1,2,3 columns are not required as these are categorical
    df1 = df.ix[:, (2, i)]   # ix performs indexing 
    cols = df.columns[i]  # to represent column names from actual dataframe in dataframe of forecasted results
    forecast_feb = timeseries_itc(df1)
    list_with_forecasted_timeperiod.append(forecast_feb[1])
    list_with_forecasted_columns.append(cols)
    list_with_forecasted_values.append(forecast_feb[0])

#Forecasted Values - 
forecasted_values = pd.DataFrame({'datetime_of_forecast': list_with_forecasted_timeperiod, 'colnames': list_with_forecasted_columns, 'forecastedvalues': list_with_forecasted_values})


##### DIP & TRIGGERS ###############################

## Write forecasted values to csv.
#forecast.to_csv("forecasted_values.csv")
## Calculating dip = Forecasted values(Let's say of Feb) - Actual Values(Let's say for Jan i.e. previous one month)
#forecast_transposed = forecast.T
#forecast_transposed = forecast_transposed.reset_index()
#forecast_transposed.columns = ["Variable", "Forecasted_Val"]

#DIP CALCULATION -
actualval_jan = list(df.iloc[33,].values) #january values. If you want feb value then change it df.iloc[34,].values and so on and so forth.
del actualval_jan[0:3]  # removing first three columns as these are categorical variables and not required.
forecasted_values['PreviousMonth_ActualVal'] =actualval_jan
forecasted_values['dip'] = forecasted_values['forecastedvalues'] - forecasted_values['PreviousMonth_ActualVal']

forecasted_values.to_csv("forecasted_values_&_dip.csv")
   
#TRIGGER CALCULATION -

 
####Step 1- Calc difference in ITC sales (forecasted val - actual value from previous month)
itcsales_forecastedvalue = forecasted_values.loc[forecasted_values['colnames'] == 'SUNFEAST_Total_Sales_Value', 'forecastedvalues']
itcsales_actualpre_value = forecasted_values.loc[forecasted_values['colnames'] == 'SUNFEAST_Total_Sales_Value', 'PreviousMonth_ActualVal']
diff_sales = itcsales_forecastedvalue- itcsales_actualpre_value   # dif sales comes out to be negative which says that there has been dip in sales of Februrary in comparision with January sales.
    ## Remove row with ITC sales from forecastedvalue dataset because we won't be using this variable 
    ## since our coefficients are calculated for independent variable which excludes ITC Sunfeast Sales.
    ## Also, we have already captured itc sales difference (forecasted - actual) under diff_sales.
forecasted_values = forecasted_values[forecasted_values.colnames != "SUNFEAST_Total_Sales_Value"]  



#### Step 2 - Read coefficients output of Ridge Regression- 
coeff = pd.read_csv("coeff_ridgeregression_cookies.csv")
coeff.columns = ['SerialNumber', 'coeff_linRidgeMod', 'colnames'] 
coeff = coeff.iloc[1:]     # 0th row is not meaningful as it contains intercept information. 
coeff.to_csv("coefficients_cookies.csv")

####Step3 - Append coeff as a new column in  existing dataframe-forecasted_values - 
results = forecasted_values.merge(coeff, on="colnames", how = 'inner')
results.to_csv("variable_report.csv") ## Detailed report explaining about variable dip, forecasted values, actual values of previous month, coefficients


list_var = []
if (diff_sales.values < 0):
    for i in range(0, len(results)):
        if ((results['dip'][i]<0) and (results['coeff_linRidgeMod'][i]<0)):
            var = results.iloc[i,1]
            list_var.append(var)    
        elif((results['dip'][i]>0) & (results['coeff_linRidgeMod'][i] > 0)):
            var1 = results.iloc[i, 1]
            list_var.append(var1)


triggers = pd.DataFrame(list_var)
triggers.columns = ["trigger_var"]
triggers.to_csv("triggerlist.csv")
       

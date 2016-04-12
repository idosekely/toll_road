Data Analysis for Israel's fast lane
====================================

why?
-----
I got curious about the prices on the Fast lane (https://www.fastlane.co.il/),
and how it correlates with the traffic

Dependencies
----------------
* pandas (pip install pandas)
* statsmodels (pip install statsmodels)
* pytools asynx (https://github.com/idosekely/pytools)
* requests (pip install requests)
* google api key (https://developers.google.com/maps/documentation/distance-matrix/get-api-key)

How it works
------------
The server samples the fast lane site using http scraping to get the price,
and samples google maps api using REST request for the traffic.<br>
the data is kept in a vertical collection (timestamp, key, value), for later analysis. <br>
<br>

Results
-------
![raw_data](https://cloud.githubusercontent.com/assets/10169406/14228468/75473078-f91e-11e5-8a7d-21e3425b47c7.png)
![rolling_mean](https://cloud.githubusercontent.com/assets/10169406/14228469/7548dbe4-f91e-11e5-840a-735e150ae660.png)
![filter](https://cloud.githubusercontent.com/assets/10169406/14228467/753e9012-f91e-11e5-8da2-cb2e2b5180e1.png)
![summary](https://cloud.githubusercontent.com/assets/10169406/14228470/754be4c4-f91e-11e5-84d5-08539f67235e.png)

Future features
---------------
* Move data to DB
* add predictions 
* move to dedicated server

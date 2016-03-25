Data Analysis for Israel's fast lane
====================================

why?
-----
I got curious about the prices on the Fast lane (https://www.fastlane.co.il/),
and how it correlates with the traffic

Dependencies
----------------
* pandas (pip install pandas)
* pytools asynx (https://github.com/idosekely/pytools)
* requests (pip install requests)
* google api key (https://developers.google.com/maps/documentation/distance-matrix/get-api-key)

How it works
------------
The server samples the fast lane site using http scraping to get the price,
and samples google maps api using REST request for the traffic.<br>
the data is kept in a vertical collection (timestamp, key, value), for later analysis. <br>
<br>

In the first version, the data is kept in csv file, and the server is simple threaded server.

Future features
---------------
* Move data to DB
* Move the REST server (like Flask)
* provide data analyzing API

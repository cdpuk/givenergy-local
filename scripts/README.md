 # Additional Scripts

This directory contains supporting scripts that may be useful for testing and debugging purposes.

The scripts have been developed against [Python](https://www.python.org/downloads/) 3.10, but will probably run on versions close to this.

With Python installed, open a command line in this directory and install the required dependencies:

```
pip3 install -r requirements.txt
```

 ## Inverter debugging

 This tool first attempts to read low-level data from an inverter, with no attempt to decode it in to meaningful values. If that works, it will also try to print out the decoded values.

 Display inverter data with no batteries:

 ```
 python3 debug.py <inverter-host>
 ```

Display data for an inverter with 2 batteries:

 ```
 python3 debug.py -b 2 <inverter-host>
 ```
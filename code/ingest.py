# python

# Please run with python ingest.py

"""
Script to fetch HTML and data from
The University of Sheffield's
COVID-19 dashboard

The flow is approximately:
- fetch, HTML from webapge (requests)
- extract, rows from HTML (html5lib/xpath)
- validate, rows as being data in expected format
- transform, data into a more regular model
- store, data as CSV and/or JSON
"""

# https://docs.python.org/3/library/xml.etree.elementtree.html
import xml.etree

# https://docs.python.org/3/library/argparse.html
import argparse

# https://docs.python.org/3/library/csv.html
import csv

# https://docs.python.org/3/library/json.html
import json

# https://dateutil.readthedocs.io/en/2.8.1/
import dateutil.parser

# https://pypi.org/project/html5lib/
import html5lib

# https://requests.readthedocs.io/en/master/
import requests

# https://www.tutorialspoint.com/matplotlib/matplotlib_bar_plot.htm
import numpy as np
import matplotlib.pyplot as plt

from datetime import date

URL = 'https://www.sheffield.ac.uk/autumn-term-2020/covid-19-statistics/'
URL_city = ('https://api.coronavirus.data.gov.uk/v1/data?'
            'filters=areaType=ltla;areaName=sheffield&'
            'structure={"date":"date","newCases":"newCasesByPublishDate"}')

def main():
    # Argument Parsing
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        type=str,
        help="Store result in .CSV file",
        dest="csv_file",
        required=False,
    )
    parser.add_argument(
        "--json",
        type=str,
        help="Store result in .JSON file",
        dest="json_file",
        required=False,
    )
    args = parser.parse_args()
    response = fetch()

    data = extract_transform_data(response)
    print('----Uni data----')
    for row in data:
        print(row)

    # Obtaining Sheffield city COVID data using GOV.UK API:
    response_city = requests.get(URL_city)
    response_city = response_city.json()['data']
    print('----City data----')
    city_data = []
    for row in response_city[::-1]:
        print([row['date'], row['newCases']])
        city_data.append([row['date'], row['newCases']])
    create_visualisations(data, city_data)

    # Converting output to CSV or JSON based on user input
    if args.csv_file is not None:
        file = args.csv_file
        with open(file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "New staff cases", "New student cases"])
            writer.writerows(data)
    elif args.json_file is not None:
        file = args.json_file
        with open(file, "w") as f:
            f.write(json.dumps(data))


def transform(rows):
    """
    The input is a list of rows, each row is a list of strings.
    The return value is a list of rows, each row is a list of
    data values.
    Dates in the first cell, are transformed into ISO 8601 date
    strings of the form YYYY-MM-DD;
    Numbers in subsequent cells, are transformed into int.

    For your convenience, the output is sorted.
    """

    result = []
    for row in rows:
        iso_date = str(dateutil.parser.parse(row[0]).date())
        out = [iso_date]
        out.extend(int(x) for x in row[1:])
        result.append(out)

    return sorted(result)


def extract(dom):
    """
    Extract all the rows that plausibly contain data,
    and return them as a list of list of strings.
    """

    rows = dom.findall(".//tr")

    result = []
    for row in rows:
        result.append([el.text for el in row])

    return result


def fetch():
    """
    Fetch the web page and return it
    """

    response = requests.get(URL)

    return response.text


def validate(table):
    """
    `table` should be a table of strings in list of list format.
    Each row is checked to see if it is of the expected format.
    A fresh table is returned (some rows are removed because
    they are "metadata").
    Invalid inputs will result in an Exception being raised.
    """

    validated = []

    for row in table:
        if "Day" in row[0]:
            assert "New staff" in row[1]
            assert "New student" in row[2]
            continue

        row = [cell_value[:-1] if cell_value.endswith('*') else cell_value for cell_value in row]
        validated.append(row)

    return validated


def extract_transform_data(response_text):
    """
    extract, clean and transform relevant data to make it usable
    """
    dom = html5lib.parse(response_text, namespaceHTMLElements=False)

    table = extract(dom)
    validated = validate(table)
    data = transform(validated)

    return data


def create_visualisations(data, city_data):
    date_column = 0
    staff_column = 1
    studentColumn = 2

    dates = []
    staff_values = []
    student_values = []

    for row in data:
        dates.append(row[date_column])
        staff_values.append(row[staff_column])
        student_values.append(row[studentColumn])

    # Restrict the Sheff City data to the same dates as the Uni data
    city_data = [row for row in city_data if row[0] in dates]
    # Use np arrays to allow vectoral algebra operations
    city_count = np.array([row[1] for row in city_data])
    staff_values= np.array(staff_values)
    student_values= np.array(student_values)
    
    # Similar implementation to https://matplotlib.org/3.1.1/gallery/lines_bars_and_markers/barchart.html
    locations = np.arange(len(dates))

    bar_width = 0.35

    fig_width, fig_height = [10, 6]
    figure, (ax1, ax2) = plt.subplots(2, 1, 
                                      sharex=True, 
                                      gridspec_kw={'hspace': 0.05,
                                                   'height_ratios' : [2,1]},
                                      figsize=(fig_width, fig_height))

    staff_bars = ax1.bar(
        locations - bar_width / 2, staff_values, bar_width, label="Staff"
    )
    student_bars = ax1.bar(
        locations + bar_width / 2, student_values, bar_width, label="Students"
    )
    

    p1 = ax2.bar(locations,
                 100*((staff_values)/city_count),
                 bar_width,
                 label='Staff')
    p2 = ax2.bar(locations,
                 100*((student_values)/city_count),
                 bar_width,
                 bottom=100*((staff_values)/city_count),
                 label='Students')
    p3 = ax2.bar(locations, 
                 100*(1-((staff_values+student_values)/city_count)),
                 bar_width,
                 bottom=100*((staff_values+student_values)/city_count),
                 label='Rest of Sheffield')
    
    ax1.plot()
    add_column_labels(staff_bars, ax1)
    add_column_labels(student_bars, ax1)
    ax1.set_title("Number of cases in staff and student populations")
    ax1.label_outer()
    ax1.legend()
    
    ax2.set_xlabel("Date")
    ax2.set_xticks(locations)
    ax2.set_xticklabels(dates)
    ax1.set_ylabel("Cases")
    ax2.set_ylabel("Relative cases [%]")
    ax2.set_ylim([0,100])
    ax2.legend()

    plt.xticks(rotation=90)
    plt.margins(0.02, 0.05)

    filename = str(date.today()) + "-staff-student-covid-cases.png"
    plt.savefig(filename, dpi=600)


def add_column_labels(bars, axes):
    for bar in bars:
        height = bar.get_height()
        axes.annotate(
            "{}".format(height),
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 1),  # Offset label by 1pt above bar
            textcoords="offset points",
            ha="center",
            va="bottom",
        )  # horizontal/vertical align


if __name__ == "__main__":
    main()

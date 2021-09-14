#!/usr/bin/python

import time
import sys
from run import check

def main(secdelay):
	"""
	calls check functionality from run.py and adds a delay in sec
	"""
	while True:
		check()
		time.sleep(secdelay)

if __name__ == "__main__":
	if len(sys.argv)>1:
		try:
			delay=int(sys.argv[1])
			main(delay)
		except ValueError:
			print("Please provide an integer.")
	else:
		print("Please provide a delay argument.")
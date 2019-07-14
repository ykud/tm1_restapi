import sys
import logging
import configparser
import getopt
import time
import csv
import TM1py
from TM1py.Services import TM1Service

def checkAxisSubset(cube,view, axis, subsetList):
	"""Check subsets used in the axis """
	dimName = axis.dimension_name
	logging.debug('Dimension : ' + dimName )
	if isinstance(axis.subset,TM1py.Objects.AnonymousSubset):
		#logging.debug('Using anonymous subset with %d elements' %len(axis.subset.elements ))
		#ALL subset doesn't have elements from REST API point of view
		if len(axis.subset.elements) == 0:
			subsetName = 'ALL'
		else:
			subsetName = 'Private Unnamed'
	else:
		logging.debug('Subset name %s' % axis.subset.name)
		subsetName = axis.subset.name
	subsetList.append({'Cube':cube,'View':view,'Dimension':dimName,'Subset':subsetName})
#
def checkView (cube_name, view_name, isPrivate, tm1, subsetList) :
	""" Go through the view columns / rows / titles and record the subsets used
	"""
	view_read_start_time = time.time()
	view_obj = tm1.cubes.views.get(cube_name = cube_name, view_name = view_name, private = isPrivate)
	logging.debug('View response in %.2f'%(time.time()-view_read_start_time))
	for col in view_obj.columns:
		checkAxisSubset(cube_name, view_name, col, subsetList)
	for row in view_obj.rows:
		checkAxisSubset(cube_name, view_name, row, subsetList)
	for title in  view_obj._titles:
		checkAxisSubset(cube_name, view_name, title, subsetList)
	logging.debug('Total view processing in %.2f'%(time.time()-view_read_start_time))
#
def main (argv):
	"""Command line format python3 analyse_views.py -s servername -o servername.csv -l servername.log """
	# getting command line arguments
	try:
		opts, args = getopt.getopt(argv, "h:s:o::l:", ["help","output=","server=","log="])
	except getopt.GetoptError:
		print (main.__doc__)
		sys.exit(2)
	if len(argv) <= 1:
		print (main.__doc__)
		sys.exit(2)
	for opt,arg in opts:
		if opt in ("-h","--help"):
			print (main.__doc__)
			sys.exit(2)
		elif opt in ("-o","--output"):
  			outputFile = arg
		elif opt in ("-s", "--server"):
			serverName = arg
		elif opt in ("-l","--log"):
			logFile = arg

	logging.basicConfig(filename=logFile,
                            filemode='w',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.INFO)
	starttime_full=time.time()
	num_cubes = 0
	num_views = 0
	num_errors = 0
	logging.info('Start processing views and identifying subsets')
	config = configparser.ConfigParser()
	config.read('config.ini')
	csvfile =  open(outputFile, 'w') 
	fieldNames = ['Cube', 'View', 'Dimension','Subset']
	writer = csv.DictWriter(csvfile, fieldnames=fieldNames, quotechar='"',quoting=csv.QUOTE_ALL)
	writer.writeheader()
	# we want to oroduct a total count of annoymous subsets by each dimension
	with TM1Service(**config[serverName], timeout=50) as tm1:
		for cube in tm1.cubes.get_model_cubes():
			num_cubes += 1
			if cube.name not in {' '}:
				logging.info('Working with cube : %s, %d / %d' % (cube.name, num_cubes, len(tm1.cubes.get_model_cubes())))
				num_private_views = 0
				num_public_views = 0
				subsetList = []
				# Meed to grab names and reqiest view details separate as REST API fails to return 1000 views in one call
				private_views, public_views = tm1.cubes.views.get_all_names(cube_name=cube.name)
				logging.info('Number of private views : ' + str(len(private_views)))
				for prview in private_views:
					num_private_views += 1
					logging.info('Processing view : %s, %d / %d ' %( prview, num_private_views, len(private_views)))
					try:
						checkView(cube.name, prview, True, tm1, subsetList)
					except Exception:
						logging.error('Error in processing view ' + prview )
						subsetList.append({'Cube':cube.name, 'View':prview, 'Dimension':'Error', 'Subset':'Error'})
						num_errors += 1
				logging.info('Number of public views : ' + str(len(public_views)))
				for pubview in public_views:
					num_public_views += 1
					logging.info('Processing view : %s, %d / %d ' %( pubview, num_public_views, len(public_views)))
					try:
						checkView(cube.name, pubview, False, tm1, subsetList)
					except Exception:
						logging.error('Error in processing view ' + pubview)
						subsetList.append({'Cube':cube.name, 'View':pubview, 'Dimension':'Error', 'Subset':'Error'})
						num_errors += 1
				num_views += num_public_views + num_private_views 
				writer.writerows(subsetList)
			num_cubes += 1
	logging.info("Processed %d cubes with %d views in " %(num_cubes, num_views) + '%.2f'%(time.time()-starttime_full) + " seconds. %d errors "%(num_errors))
if __name__ == "__main__":
    main(sys.argv[1:])
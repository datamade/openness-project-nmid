s3/$(AWS_STORAGE_BUCKET_NAME)/%.gz : %.gz
	aws s3 cp $< s3://$$AWS_STORAGE_BUCKET_NAME

%.gz : _data/raw/%.csv
	gzip -c $< > $@

_data/raw/CON_%.csv : 
	wget --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$*&transactionType=CON&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

data/raw/EXP_%.csv :
	wget --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$*&transactionType=EXP&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

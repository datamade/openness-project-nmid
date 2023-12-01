.PRECIOUS : _data/raw/%.csv

import/% : s3/$(AWS_STORAGE_BUCKET_NAME)/%.gz
	python manage.py import_api_data --transaction-type $(word 1, $(subst _, , $*)) \
		--year $(word 2, $(subst _, , $*))

import/local/% : _data/raw/%.csv
		python manage.py import_api_data --transaction-type $(word 1, $(subst _, , $*)) \
			--year $(word 2, $(subst _, , $*)) \
			--file $<

s3/$(AWS_STORAGE_BUCKET_NAME)/%.gz : %.gz
	aws s3 cp $< s3://$$AWS_STORAGE_BUCKET_NAME

%.gz : _data/raw/%.csv
	gzip -c $< > $@

_data/raw/%.csv : 
	wget --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$(word 2, $(subst _, , $*))&transactionType=$(word 1, $(subst _, , $*))&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

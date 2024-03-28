
.PHONY : quarterly
quarterly: import/candidates import/CON_2020 import/EXP_2020 import/CON_2021 import/EXP_2021 import/CON_2022 import/EXP_2022 import/CON_2023 import/EXP_2023 import/CON_2024 import/EXP_2024

.PHONY : nightly
nightly: import/candidates import/CON_2023 import/EXP_2023 import/CON_2024 import/EXP_2024

import/% : _data/raw/%.csv
	python manage.py import_api_data --transaction-type $(word 1, $(subst _, , $*)) \
		--year $(word 2, $(subst _, , $*)) \
		--file $<

import/candidates : _data/raw/candidate_committees.csv
	python manage.py import_candidate_api_data --file $<

_data/raw/candidate_committees.csv :
	wget --no-use-server-timestamps -O $@ "https://openness-project-nmid.s3.amazonaws.com/candidate_committees.csv"

_data/raw/CON_%.csv :
	wget --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$(word 2, $(subst _, , $*))&transactionType=$(word 1, $(subst _, , $*))&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

_data/raw/EXP_%.csv :
	wget --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$(word 2, $(subst _, , $*))&transactionType=$(word 1, $(subst _, , $*))&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

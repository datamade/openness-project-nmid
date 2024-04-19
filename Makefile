
.PHONY : quarterly
quarterly: import/candidates import/pacs import/CON_2020 import/EXP_2020 import/CON_2021 import/EXP_2021 import/CON_2022 import/EXP_2022 import/CON_2023 import/EXP_2023 import/CON_2024 import/EXP_2024

.PHONY : nightly
nightly: import/candidates import/pacs import/CON_2023 import/EXP_2023 import/CON_2024 import/EXP_2024


import/% : _data/sorted/%.csv
	python manage.py import_api_data --transaction-type $(word 1, $(subst _, , $*)) \
		--year $(word 2, $(subst _, , $*)) \
		--file $<

import/pac_filings : _data/raw/pac_committee_filings.csv
	python manage.py import_pac_filings --file $<

import/candidate_filings : _data/raw/candidate_committee_filings.csv
	python manage.py import_candidate_filings --file $<

import/candidates : _data/raw/candidate_committees.csv
	python manage.py import_candidate_api_data --file $<

import/pacs : _data/raw/pac_committees.csv
	python manage.py import_pac_api_data --file $<


_data/raw/candidate_committees.csv :
	wget --no-use-server-timestamps -O $@ "https://openness-project-nmid.s3.amazonaws.com/candidate_committees.csv"

_data/sorted/%.csv : _data/raw/%.csv
	xsv fixlengths $< | xsv sort -s OrgID,"Report Name","Start of Period","End of Period" > $@

_data/raw/CON_%.csv :
	wget --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$(word 2, $(subst _, , $*))&transactionType=$(word 1, $(subst _, , $*))&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

_data/raw/EXP_%.csv :
	wget --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$(word 2, $(subst _, , $*))&transactionType=$(word 1, $(subst _, , $*))&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

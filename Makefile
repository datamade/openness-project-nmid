
.PHONY : quarterly
quarterly: import/candidates import/pacs import/candidate_filings import/pac_filings import/CON_2020 import/EXP_2020 import/CON_2021 import/EXP_2021 import/CON_2022 import/EXP_2022 import/CON_2023 import/EXP_2023 import/CON_2024 import/EXP_2024
	python manage.py make_search_index

.PHONY : nightly
nightly: import/candidates import/pacs import/candidate_filings import/pac_filings import/CON_2023 import/EXP_2023 import/CON_2024 import/EXP_2024
	python manage.py make_search_index

import/% : _data/sorted/%.csv
	python manage.py import_transactions --transaction-type $(word 1, $(subst _, , $*)) \
		--year $(word 2, $(subst _, , $*)) \
		--file $<

import/pac_filings : _data/raw/pac_committee_filings.csv
	python manage.py import_pac_filings --file $<

import/candidate_filings : _data/raw/candidate_committee_filings.csv
	python manage.py import_candidate_filings --file $<

import/candidates : _data/raw/candidate_committees.csv
	python manage.py import_candidates --file $<

import/pacs : _data/raw/pac_committees.csv
	python manage.py import_pac_committees --file $<

_data/raw/%_committees.csv :
	wget --no-use-server-timestamps -O $@ "https://openness-project-nmid.s3.amazonaws.com/$*_committees.csv"

_data/raw/%_committee_filings.csv :
	wget --no-use-server-timestamps -O $@ "https://openness-project-nmid.s3.amazonaws.com/$*_committee_filings.csv"


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

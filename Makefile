THIS_YEAR=$(shell date +"%Y")
NIGHTLY_YEARS=$(shell seq 2023 $(THIS_YEAR))
QUARTERLY_YEARS=$(shell seq 2020 $(THIS_YEAR))

define quarterly_target
	$(foreach YEAR,$(1),$(patsubst %,import/$(2)_%_$(YEAR),1 2 3 4))
endef

.PHONY : quarterly
quarterly: import/candidates import/pacs import/candidate_filings import/pac_filings \
	$(call quarterly_target,$(QUARTERLY_YEARS),CON) $(call quarterly_target,$(QUARTERLY_YEARS),EXP)
	python manage.py make_search_index

.PHONY : nightly
nightly: import/candidates import/pacs import/candidate_filings import/pac_filings \
	$(call quarterly_target,$(NIGHTLY_YEARS),CON) $(call quarterly_target,$(NIGHTLY_YEARS),EXP)
	python manage.py make_search_index

.SECONDEXPANSION:
import/% : _data/sorted/$$(word 1, $$(subst _, , $$*))_$$(word 3, $$(subst _, , $$*)).csv
	python manage.py import_transactions --transaction-type $(word 1, $(subst _, , $*)) \
		--quarters $(word 2, $(subst _, , $*)) \
		--file-year $(word 3, $(subst _, , $*)) \
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
	wget --no-check-certificate --no-use-server-timestamps -O $@ "https://openness-project-nmid.s3.amazonaws.com/$*_committees.csv"

_data/raw/%_committee_filings.csv :
	wget --no-check-certificate --no-use-server-timestamps -O $@ "https://openness-project-nmid.s3.amazonaws.com/$*_committee_filings.csv"

_data/sorted/%.csv : _data/raw/%.csv
	xsv fixlengths $< | xsv sort -s OrgID,"Report Name","Start of Period","End of Period" > $@

_data/raw/CON_%.csv :
	wget --no-check-certificate --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$(word 2, $(subst _, , $*))&transactionType=$(word 1, $(subst _, , $*))&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

_data/raw/EXP_%.csv :
	wget --no-check-certificate --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$(word 2, $(subst _, , $*))&transactionType=$(word 1, $(subst _, , $*))&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

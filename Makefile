
.PHONY : quarterly
quarterly: import/offices import/CON_2020 import/EXP_2020 import/CON_2021 import/EXP_2021 import/CON_2022 import/EXP_2022 import/CON_2023 import/EXP_2023 import/CON_2024 import/EXP_2024

.PHONY : nightly
nightly: import/offices import/CON_2023 import/EXP_2023 import/CON_2024 import/EXP_2024

import/% : _data/raw/%.csv
	python manage.py import_api_data --transaction-type $(word 1, $(subst _, , $*)) \
		--year $(word 2, $(subst _, , $*)) \
		--file $<

import/offices :
	python manage.py import_office_api_data

_data/raw/%.csv : 
	wget --no-use-server-timestamps \
		"https://login.cfis.sos.state.nm.us/api/DataDownload/GetCSVDownloadReport?year=$(word 2, $(subst _, , $*))&transactionType=$(word 1, $(subst _, , $*))&reportFormat=csv&fileName=$(notdir $@)" \
		-O $@

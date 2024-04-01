CREATE OR REPLACE FUNCTION update_anonymous() RETURNS TRIGGER AS $update_anonymous$
    DECLARE
        myrec VARCHAR;
    BEGIN

        IF (TG_OP = 'UPDATE' OR TG_OP = 'INSERT') THEN
            IF (coalesce(trim(concat_ws(' ',
                                        NEW.company_name,
                                        NEW.name_prefix,
                                        NEW.first_name,
                                        NEW.middle_name,
                                        NEW.last_name,
                                        NEW.suffix)), '') = '') THEN

                EXECUTE format('UPDATE camp_fin_transaction SET
                                  search_name = to_tsvector(%L, %L)
                                WHERE id = %L', E'english', E'Anonymous', NEW.id);

            END IF;
            RETURN NEW;
        END IF;
        RETURN NEW;
    END;
$update_anonymous$ LANGUAGE plpgsql;

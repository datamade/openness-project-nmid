CREATE OR REPLACE FUNCTION drop_triggers() RETURNS text AS $$ DECLARE
    _rec RECORD;
BEGIN
    FOR _rec IN select distinct event_object_table, trigger_name from information_schema.triggers where trigger_schema = 'public' and trigger_name like '%_search_update' LOOP
        RAISE NOTICE 'Dropping trigger: % on table: %', _rec.trigger_name, _rec.event_object_table;
        EXECUTE 'DROP TRIGGER ' || _rec.trigger_name || ' ON ' || _rec.event_object_table || ';';
    END LOOP;

    RETURN 'done';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

select drop_triggers();
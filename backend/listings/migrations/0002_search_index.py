from django.db import migrations


FORWARD = """
CREATE VIRTUAL TABLE listings_search USING fts5(title, description, area, attributes, tokenize='unicode61 remove_diacritics 2');
INSERT INTO listings_search(rowid, title, description, area, attributes)
SELECT id, replace(replace(json_extract(published, '$.title'), 'đ', 'd'), 'Đ', 'D'), replace(replace(json_extract(published, '$.description'), 'đ', 'd'), 'Đ', 'D'),
replace(replace(json_extract(published, '$.area'), 'đ', 'd'), 'Đ', 'D'), replace(replace(json_extract(published, '$.attributes'), 'đ', 'd'), 'Đ', 'D') FROM listings_listing;
CREATE TRIGGER listings_search_insert AFTER INSERT ON listings_listing BEGIN
INSERT INTO listings_search(rowid, title, description, area, attributes) VALUES
(new.id, replace(replace(json_extract(new.published, '$.title'), 'đ', 'd'), 'Đ', 'D'), replace(replace(json_extract(new.published, '$.description'), 'đ', 'd'), 'Đ', 'D'),
replace(replace(json_extract(new.published, '$.area'), 'đ', 'd'), 'Đ', 'D'), replace(replace(json_extract(new.published, '$.attributes'), 'đ', 'd'), 'Đ', 'D'));
END;
CREATE TRIGGER listings_search_update AFTER UPDATE OF published ON listings_listing BEGIN
DELETE FROM listings_search WHERE rowid=old.id;
INSERT INTO listings_search(rowid, title, description, area, attributes) VALUES
(new.id, replace(replace(json_extract(new.published, '$.title'), 'đ', 'd'), 'Đ', 'D'), replace(replace(json_extract(new.published, '$.description'), 'đ', 'd'), 'Đ', 'D'),
replace(replace(json_extract(new.published, '$.area'), 'đ', 'd'), 'Đ', 'D'), replace(replace(json_extract(new.published, '$.attributes'), 'đ', 'd'), 'Đ', 'D'));
END;
CREATE TRIGGER listings_search_delete AFTER DELETE ON listings_listing BEGIN
DELETE FROM listings_search WHERE rowid=old.id;
END;
"""
REVERSE = """
DROP TRIGGER listings_search_delete;
DROP TRIGGER listings_search_update;
DROP TRIGGER listings_search_insert;
DROP TABLE listings_search;
"""


class Migration(migrations.Migration):
    dependencies = [('listings', '0001_initial')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

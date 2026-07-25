{{ config(alias='capology_wages') }}

SELECT * FROM {{ source('raw', 'capology_wages') }}

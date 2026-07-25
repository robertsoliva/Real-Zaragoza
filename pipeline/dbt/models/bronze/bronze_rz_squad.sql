{{ config(alias='rz_squad') }}

SELECT * FROM {{ source('raw', 'transfermarkt_squad') }}

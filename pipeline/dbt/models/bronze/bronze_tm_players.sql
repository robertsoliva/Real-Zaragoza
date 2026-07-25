{{ config(alias='tm_players') }}

SELECT * FROM {{ source('raw', 'transfermarkt_players') }}

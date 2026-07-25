{{ config(alias='rz_squad') }}

SELECT * FROM {{ source('raw', 'transfermarkt_players') }}
WHERE LOWER(club_name) LIKE '%zaragoza%'

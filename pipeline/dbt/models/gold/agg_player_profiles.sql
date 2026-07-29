{{ config(cluster_by=['position_group', 'season_id'], tags=['player_clustering']) }}

-- Player archetype clustering. One BQML k-means model per position group
-- (ml.player_cluster_<group>), trained on ml.player_profile_features
-- (MICE-imputed, TM-position-labeled player-seasons; see
-- pipeline/cloud-run/player-clustering/). k chosen per group via BQML native
-- hyperparameter tuning (num_clusters HPARAM_RANGE 2-8, Davies-Bouldin
-- objective) rather than a pre-defined k. ML.PREDICT defaults to each
-- model's optimal trial.
--
-- Scope: only player-seasons with a real TM granular position match (the
-- ~7k rows in ml.player_profile_features). Players with only a broad
-- SofaScore D/M/F/G code are NOT included -- there's no safe way to pick a
-- single position group for them (SofaScore "M" could be DM, CM, or CAM,
-- each scored on different features), so extending coverage requires a
-- follow-up rather than a guessed mapping. See next-actions.md.
--
-- profile_label is assigned by hand from each cluster's centroid values
-- (ML.CENTROIDS), not learned -- re-verify labels if the seed/training data
-- changes materially (next TM quarterly refresh) since centroid_id ordering
-- can shift between retrains.

WITH cb AS (
  SELECT
    sofascore_id, player_name, team_name, league_name, tournament_id, season_id,
    position_group, CENTROID_ID AS cluster_id,
    CASE CENTROID_ID
      WHEN 1 THEN 'Dominant Aerial CB'
      WHEN 2 THEN 'Positional / Reader CB'
      WHEN 3 THEN 'Combative CB'
      WHEN 4 THEN 'Ball-Playing CB'
    END AS profile_label
  FROM ML.PREDICT(MODEL `{{ target.project }}.ml.player_cluster_cb`,
    (SELECT * FROM `{{ target.project }}.ml.player_profile_features` WHERE position_group = 'CB'))
),

fb AS (
  SELECT
    sofascore_id, player_name, team_name, league_name, tournament_id, season_id,
    position_group, CENTROID_ID AS cluster_id,
    CASE CENTROID_ID
      WHEN 1 THEN 'Attacking / Overlapping FB'
      WHEN 2 THEN 'Defensive FB'
      WHEN 3 THEN 'Conservative FB'
      WHEN 4 THEN 'Attacking Specialist (weak defensively)'
    END AS profile_label
  FROM ML.PREDICT(MODEL `{{ target.project }}.ml.player_cluster_fb`,
    (SELECT * FROM `{{ target.project }}.ml.player_profile_features` WHERE position_group = 'FB'))
),

dm AS (
  SELECT
    sofascore_id, player_name, team_name, league_name, tournament_id, season_id,
    position_group, CENTROID_ID AS cluster_id,
    CASE CENTROID_ID
      WHEN 1 THEN 'Ball-Winning DM'
      WHEN 2 THEN 'Complete DM'
      WHEN 3 THEN 'Deep-Lying Playmaker'
      WHEN 4 THEN 'Destroyer / Enforcer'
      WHEN 5 THEN 'Limited / Raw DM'
    END AS profile_label
  FROM ML.PREDICT(MODEL `{{ target.project }}.ml.player_cluster_dm`,
    (SELECT * FROM `{{ target.project }}.ml.player_profile_features` WHERE position_group = 'DM'))
),

cm AS (
  SELECT
    sofascore_id, player_name, team_name, league_name, tournament_id, season_id,
    position_group, CENTROID_ID AS cluster_id,
    CASE CENTROID_ID
      WHEN 1 THEN 'Creative / Attacking CM'
      WHEN 2 THEN 'Low-Impact CM'
      WHEN 3 THEN 'Box-to-Box / Defensive CM'
      WHEN 4 THEN 'Inconsistent / Raw CM'
    END AS profile_label
  FROM ML.PREDICT(MODEL `{{ target.project }}.ml.player_cluster_cm`,
    (SELECT * FROM `{{ target.project }}.ml.player_profile_features` WHERE position_group = 'CM'))
),

cam AS (
  SELECT
    sofascore_id, player_name, team_name, league_name, tournament_id, season_id,
    position_group, CENTROID_ID AS cluster_id,
    CASE CENTROID_ID
      WHEN 1 THEN 'Fringe / Impact-Sub CAM'
      WHEN 2 THEN 'Goal-Threat CAM'
      WHEN 3 THEN 'Chance-Creator CAM'
      WHEN 4 THEN 'Deep-Lying Creator CAM'
      WHEN 5 THEN 'Elite All-Around CAM'
      WHEN 6 THEN 'Squad / Rotation CAM'
      WHEN 7 THEN 'Assist-Focused CAM'
      WHEN 8 THEN 'High-Volume, Low-Accuracy CAM'
    END AS profile_label
  FROM ML.PREDICT(MODEL `{{ target.project }}.ml.player_cluster_cam`,
    (SELECT * FROM `{{ target.project }}.ml.player_profile_features` WHERE position_group = 'CAM'))
),

winger AS (
  SELECT
    sofascore_id, player_name, team_name, league_name, tournament_id, season_id,
    position_group, CENTROID_ID AS cluster_id,
    CASE CENTROID_ID
      WHEN 1 THEN 'Direct / Shooting Winger'
      WHEN 2 THEN 'Creative Hub Winger'
      WHEN 3 THEN 'Two-Way Winger'
      WHEN 4 THEN 'Limited / Squad Winger'
      WHEN 5 THEN 'Out-and-Out Crosser'
    END AS profile_label
  FROM ML.PREDICT(MODEL `{{ target.project }}.ml.player_cluster_winger`,
    (SELECT * FROM `{{ target.project }}.ml.player_profile_features` WHERE position_group = 'Winger'))
),

cf AS (
  SELECT
    sofascore_id, player_name, team_name, league_name, tournament_id, season_id,
    position_group, CENTROID_ID AS cluster_id,
    CASE CENTROID_ID
      WHEN 1 THEN 'Squad-Level Forward'
      WHEN 2 THEN 'Poacher'
      WHEN 3 THEN 'Low-Impact Forward'
      WHEN 4 THEN 'Link-Up Forward'
      WHEN 5 THEN 'Target Man'
      WHEN 6 THEN 'Complete / Physical Forward'
      WHEN 7 THEN 'High-Volume Shooter'
      WHEN 8 THEN 'Elite Clinical Finisher'
    END AS profile_label
  FROM ML.PREDICT(MODEL `{{ target.project }}.ml.player_cluster_cf`,
    (SELECT * FROM `{{ target.project }}.ml.player_profile_features` WHERE position_group = 'CF'))
)

SELECT * FROM cb
UNION ALL SELECT * FROM fb
UNION ALL SELECT * FROM dm
UNION ALL SELECT * FROM cm
UNION ALL SELECT * FROM cam
UNION ALL SELECT * FROM winger
UNION ALL SELECT * FROM cf

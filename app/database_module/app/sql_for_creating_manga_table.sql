CREATE TABLE `manga_list` (
  `id_default` int(5) NOT NULL AUTO_INCREMENT,
  `id_anilist` int(11) NOT NULL,
  `id_mal` int(11) DEFAULT NULL,
  `title_english` varchar(255) DEFAULT NULL,
  `title_romaji` varchar(255) DEFAULT NULL,
  `on_list_status` varchar(255) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `media_format` varchar(255) DEFAULT NULL,
  `all_chapters` int(11) DEFAULT 0,
  `all_volumes` int(11) DEFAULT 0,
  `chapters_progress` int(11) DEFAULT 0,
  `volumes_progress` int(11) DEFAULT 0,
  `score` float DEFAULT 0,
  `reread_times` int(11) DEFAULT 0,
  `cover_image` varchar(255) DEFAULT NULL,
  `is_favourite` INT(11) DEFAULT 0,
  `anilist_url` varchar(255) DEFAULT NULL,
  `mal_url` varchar(255) DEFAULT NULL,
  `last_updated_on_site` timestamp NULL DEFAULT NULL,
  `entry_createdAt` timestamp NULL DEFAULT NULL,
  `user_startedAt` text DEFAULT 'not started',
  `user_completedAt` text DEFAULT 'not completed',
  `notes` text DEFAULT NULL,
  `description` text DEFAULT NULL,
  `country_of_origin` varchar(255) DEFAULT NULL,
  `media_start_date` text DEFAULT 'media not started',
  `media_end_date` text DEFAULT 'media not ended',
  `genres` text DEFAULT 'none genres provided',
  `external_links` text DEFAULT 'none links associated',
  PRIMARY KEY (`id_default`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
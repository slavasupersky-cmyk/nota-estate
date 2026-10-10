<?php
// Настройки приёма заявок. Этот файл — ОБРАЗЕЦ, ключей в репозитории нет.
// На хостинге: Файловый менеджер → папка nota.expert (та, где лежит docs, а не внутри docs)
// → создать файл nota-config.php → вставить этот текст и вписать свой ключ GitHub.
return [
  'gh_repo'  => 'slavasupersky-cmyk/nota-leads',   // закрытый репозиторий с Action, который пишет в Telegram
  'gh_token' => 'СЮДА_КЛЮЧ_GITHUB',                 // fine-grained token: доступ только к nota-leads, Contents: Read and write
];

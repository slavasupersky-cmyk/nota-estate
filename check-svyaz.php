<?php
// Одноразовая проверка: видит ли хостинг Telegram и GitHub. Ключей и данных не содержит. Удалить после проверки.
header('Content-Type: text/plain; charset=utf-8');
header('X-Robots-Tag: noindex');
echo "PHP " . PHP_VERSION . "\n";
echo "curl: " . (function_exists('curl_init') ? 'есть' : 'нет') . "\n";
echo "imap: " . (function_exists('imap_open') ? 'есть' : 'нет') . "\n";
echo "mail(): " . (function_exists('mail') ? 'есть' : 'нет') . "\n\n";
$targets = [
  'Telegram API' => 'https://api.telegram.org/',
  'GitHub API'   => 'https://api.github.com/',
  'Cloudflare'   => 'https://workers.cloudflare.com/',
  'Яндекс (контроль)' => 'https://ya.ru/',
];
foreach ($targets as $name => $url) {
  if (!function_exists('curl_init')) { echo "$name: нет curl\n"; continue; }
  $t = microtime(true);
  $ch = curl_init($url);
  curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_NOBODY => true, CURLOPT_TIMEOUT => 10, CURLOPT_CONNECTTIMEOUT => 8, CURLOPT_FOLLOWLOCATION => false]);
  curl_exec($ch);
  $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
  $err = curl_error($ch);
  curl_close($ch);
  $ms = round((microtime(true) - $t) * 1000);
  echo str_pad($name, 20) . ($code ? "ответ $code за {$ms} мс" : "НЕ ДОСТУПЕН ($err), {$ms} мс") . "\n";
}

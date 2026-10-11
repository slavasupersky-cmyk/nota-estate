<?php
// Прокси к API Яндекс Вебмастера для сборщика «Цифры NOTA» (репозиторий nota-leads).
// Из GitHub (серверы в США) api.webmaster.yandex.net не отвечает, с хостинга в России — отвечает.
// Токен здесь не хранится: сборщик присылает его в заголовке X-WM-Token, и он уходит только в api.webmaster.yandex.net.
// Пускаем только на чтение: пользователь, список сайтов, сводка сайта, популярные запросы.
header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');

function out($code, $body) { http_response_code($code); echo $body; exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'GET') out(405, '{"error":"method"}');
$target = (string)($_GET['p'] ?? '');
$path = explode('?', $target, 2)[0];
if (!preg_match('~^/v4/user(/[0-9]{1,20}/hosts(/[A-Za-z0-9%:._\-]{1,120}/(summary|search-queries/popular))?)?/?$~', $path)) out(400, '{"error":"path"}');
$token = (string)($_SERVER['HTTP_X_WM_TOKEN'] ?? '');
if (!preg_match('~^[A-Za-z0-9_\-]{20,120}$~', $token)) out(401, '{"error":"token"}');
if (!function_exists('curl_init')) out(500, '{"error":"curl"}');

$ch = curl_init('https://api.webmaster.yandex.net' . $target);
curl_setopt_array($ch, [
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_TIMEOUT => 25,
  CURLOPT_HTTPHEADER => ['Authorization: OAuth ' . $token, 'Accept: application/json', 'User-Agent: nota-metrics/1.0'],
]);
$body = curl_exec($ch);
$code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
if ($body === false || $code === 0) out(502, '{"error":"upstream"}');
out($code, $body);

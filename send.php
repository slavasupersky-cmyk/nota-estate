<?php
// Приём заявок с форм сайта (js/nota.js шлёт сюда JSON).
// 1) Заявка сразу сохраняется в файл на хостинге (папка leads/ рядом с docs, из интернета не видна).
// 2) Письмо на hello@nota.expert — всегда.
// 3) В Telegram — через GitHub: хостинг nic.ru до api.telegram.org не достаёт, а до GitHub — да.
//    Хостинг будит Action в закрытом репозитории nota-leads, тот пишет в группу «Заявки NOTA».
// Ключи — НЕ здесь, а в /home/not7954625/nota.expert/nota-config.php (вне папки сайта).
// Образец: tools/leads/nota-config.example.php

ini_set('display_errors', '0');
error_reporting(0);
date_default_timezone_set('Europe/Moscow');
header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex');
header('Cache-Control: no-store');

function out($ok, $code = 200) { http_response_code($code); echo json_encode(['ok' => $ok]); exit; }
function cut($s, $n) {
  $s = trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', (string)$s) ?? '');
  return function_exists('mb_substr') ? mb_substr($s, 0, $n) : substr($s, 0, $n * 2);
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') out(false, 405);
$in = json_decode((string)file_get_contents('php://input', false, null, 0, 40000), true);
if (!is_array($in)) out(false, 400);

// ловушки для ботов: заполнено скрытое поле или форму отправили быстрее 2 секунд — «принимаем» и молча выбрасываем
if (!empty($in['hp']) || (int)($in['t'] ?? 0) < 2000) out(true);

$fields = [];
foreach (array_slice((array)($in['fields'] ?? []), 0, 14) as $f) {
  if (!is_array($f) || count($f) < 2) continue;
  $k = cut($f[0], 80); $v = cut($f[1], 2000);
  if ($v !== '') $fields[] = [$k ?: 'Поле', $v];
}
if (!$fields) out(false, 400);
$form = cut($in['form'] ?? '', 150);
$sum  = cut($in['sum'] ?? '', 1500);
$page = cut($in['page'] ?? '', 200);
$path = cut($in['path'] ?? '', 300);

// не больше 5 заявок за 10 минут с одного адреса
$dir = dirname(__DIR__) . '/leads';
if (!is_dir($dir)) @mkdir($dir, 0700, true);
$rl = $dir . '/.rl-' . substr(sha1(($_SERVER['REMOTE_ADDR'] ?? '') . '|nota'), 0, 16);
$now = time();
$hits = array_filter(explode(',', (string)@file_get_contents($rl)), function ($x) use ($now) { return $x !== '' && $now - (int)$x < 600; });
if (count($hits) >= 5) out(false, 429);
$hits[] = $now;
@file_put_contents($rl, implode(',', $hits), LOCK_EX);

$lines = ['Заявка с сайта' . ($form !== '' ? ' — ' . $form : '')];
foreach ($fields as $f) $lines[] = $f[0] . ': ' . $f[1];
if ($sum !== '') $lines[] = 'Ответы в анкете: ' . $sum;
$lines[] = 'Страница: ' . ($page !== '' ? $page . ' — ' : '') . 'https://nota.expert' . ($path !== '' && $path[0] === '/' ? $path : '/');
$lines[] = 'Пришла: ' . date('d.m.Y H:i') . ' МСК';
$text = implode("\n", $lines);

// 1. копия в файл — заявка не потеряется, даже если почта и GitHub недоступны
$saved = @file_put_contents($dir . '/' . date('Y-m') . '.txt', "-----\n" . $text . "\n", FILE_APPEND | LOCK_EX) !== false;

// 2. письмо
$to = 'hello@nota.expert';
$subject = '=?UTF-8?B?' . base64_encode('Заявка: ' . cut($form !== '' ? $form : 'сайт', 70)) . '?=';
$headers = "From: =?UTF-8?B?" . base64_encode('Сайт NOTA') . "?= <hello@nota.expert>\r\n"
         . "MIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64";
$body = chunk_split(base64_encode($text));
$mailOk = @mail($to, $subject, $body, $headers, '-fhello@nota.expert');
if (!$mailOk) $mailOk = @mail($to, $subject, $body, $headers);

// 3. Telegram через GitHub
$ghCode = 0;
$cfgFile = dirname(__DIR__) . '/nota-config.php';
$cfg = is_file($cfgFile) ? (include $cfgFile) : [];
if (is_array($cfg) && !empty($cfg['gh_token']) && !empty($cfg['gh_repo']) && function_exists('curl_init')) {
  $ch = curl_init('https://api.github.com/repos/' . $cfg['gh_repo'] . '/dispatches');
  curl_setopt_array($ch, [
    CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 8, CURLOPT_CONNECTTIMEOUT => 5,
    CURLOPT_HTTPHEADER => [
      'Accept: application/vnd.github+json', 'X-GitHub-Api-Version: 2022-11-28',
      'Authorization: Bearer ' . $cfg['gh_token'], 'User-Agent: nota-expert-leads', 'Content-Type: application/json',
    ],
    CURLOPT_POSTFIELDS => json_encode(['event_type' => 'lead', 'client_payload' => ['text' => $text]], JSON_UNESCAPED_UNICODE),
  ]);
  curl_exec($ch);
  $ghCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
}
$tgOk = $ghCode === 204;

// журнал доставки без личных данных: видно, если что-то из каналов перестало работать
@file_put_contents($dir . '/dostavka.log', date('Y-m-d H:i') . ' почта:' . ($mailOk ? 'да' : 'НЕТ') . ' github:' . ($ghCode ?: 'нет ключа') . ' файл:' . ($saved ? 'да' : 'НЕТ') . "\n", FILE_APPEND | LOCK_EX);

out($mailOk || $tgOk);

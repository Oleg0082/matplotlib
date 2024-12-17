<?php
session_start();

error_reporting(E_ALL);
ini_set('display_errors', 1);

$db_name = 'graficaspersonales.sqlite3';
if (!file_exists($db_name)) {
    touch($db_name);
}

function get_db_conn() {
    global $db_name;
    $conn = new SQLite3($db_name);
    $conn->enableExceptions(true);
    return $conn;
}

function init_db() {
    $conn = get_db_conn();
    $conn->exec("
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        );
    ");
    $conn->exec("
        CREATE TABLE IF NOT EXISTS dataset_config (
            stat_name TEXT,
            user_id INTEGER,
            chart_type TEXT,
            chart_color TEXT,
            PRIMARY KEY(stat_name, user_id)
        );
    ");
    $conn->close();
}

init_db();

function is_valid_stat_name($name) {
    return preg_match('/^[A-Za-z0-9_]+$/', $name);
}

function get_user_id() {
    return isset($_SESSION['user_id']) ? $_SESSION['user_id'] : null;
}

function user_is_logged_in() {
    return isset($_SESSION['user_id']);
}

function get_datasets_for_user($user_id) {
    $conn = get_db_conn();
    $stmt = $conn->prepare("SELECT stat_name FROM dataset_config WHERE user_id = ?");
    $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
    $res = $stmt->execute();
    $datasets = [];
    while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
        $datasets[] = $row['stat_name'];
    }
    $conn->close();
    return $datasets;
}

function full_table_name($user_id, $stat_name) {
    return "user_{$user_id}_{$stat_name}";
}

$action = isset($_GET['action']) ? $_GET['action'] : null;

header('Content-Type: application/json; charset=utf-8');

switch ($action) {
    case 'check_login':
        echo json_encode(['logged_in' => user_is_logged_in()]);
        break;

    case 'login':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $username = trim($_POST['username'] ?? '');
            $password = trim($_POST['password'] ?? '');
            $conn = get_db_conn();
            $stmt = $conn->prepare("SELECT id, password FROM users WHERE username=?");
            $stmt->bindValue(1, $username, SQLITE3_TEXT);
            $res = $stmt->execute();
            $row = $res->fetchArray(SQLITE3_ASSOC);
            $conn->close();
            if ($row && $row['password'] === $password) {
                $_SESSION['user_id'] = $row['id'];
                echo json_encode(['result' => 'ok']);
            } else {
                // Can't easily redirect here, so just return error and handle on frontend or login page
                echo json_encode(['error' => 'Usuario o contraseña incorrectos']);
            }
        } else {
            echo json_encode(['error' => 'Método no soportado']);
        }
        break;

    case 'signup':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $username = trim($_POST['username'] ?? '');
            $password = trim($_POST['password'] ?? '');
            if (!$username || !$password) {
                echo json_encode(['error' => 'Se requieren nombre de usuario y contraseña']);
                break;
            }
            $conn = get_db_conn();
            $stmt = $conn->prepare("INSERT INTO users (username, password) VALUES (?,?)");
            $stmt->bindValue(1, $username, SQLITE3_TEXT);
            $stmt->bindValue(2, $password, SQLITE3_TEXT);
            try {
                $stmt->execute();
                $conn->close();
                echo json_encode(['result' => 'ok']);
            } catch (Exception $e) {
                $conn->close();
                echo json_encode(['error' => 'El nombre de usuario ya existe']);
            }
        } else {
            echo json_encode(['error' => 'Método no soportado']);
        }
        break;

    case 'logout':
        session_destroy();
        echo json_encode(['result' => 'ok']);
echo '<script type="text/javascript">window.location.href = "login.html";</script>';

        break;

    case 'datasets':
        if (user_is_logged_in()) {
            $datasets = get_datasets_for_user(get_user_id());
            echo json_encode($datasets);
        } else {
            echo json_encode([]);
        }
        break;

    case 'create_dataset':
        if (!user_is_logged_in()) {
            http_response_code(403);
            echo json_encode(['error' => 'No ha iniciado sesión']);
            break;
        }
        $user_id = get_user_id();
        $stat_name = trim($_POST['stat_name'] ?? '');
        $chart_type = trim($_POST['chart_type'] ?? 'bar');
        $chart_color = trim($_POST['chart_color'] ?? '#4CAF50');

        if (!$stat_name) {
            echo json_encode(['error' => 'El nombre de la estadística no puede estar vacío']);
            break;
        }
        if (!is_valid_stat_name($stat_name)) {
            echo json_encode(['error' => 'Nombre de estadística inválido. Use solo letras, dígitos y guiones bajos.']);
            break;
        }
        if (!in_array($chart_type, ['bar','pie'])) {
            echo json_encode(['error' => 'Tipo de gráfico inválido. Debe ser barras o pastel.']);
            break;
        }
        if ($chart_type === 'pie') {
            $chart_color = '';
        }

        $conn = get_db_conn();
        $stmt = $conn->prepare("SELECT COUNT(*) as cnt FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        if ($row['cnt'] > 0) {
            $conn->close();
            echo json_encode(['error' => 'Ya existe una estadística con ese nombre para este usuario.']);
            break;
        }

        $table_name = full_table_name($user_id, $stat_name);
        $conn->exec("CREATE TABLE IF NOT EXISTS \"$table_name\" (etiqueta TEXT, valor REAL)");
        $stmt = $conn->prepare("REPLACE INTO dataset_config (stat_name, user_id, chart_type, chart_color) VALUES (?,?,?,?)");
        $stmt->bindValue(1, $stat_name, SQLITE3_TEXT);
        $stmt->bindValue(2, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(3, $chart_type, SQLITE3_TEXT);
        $stmt->bindValue(4, $chart_color, SQLITE3_TEXT);
        $stmt->execute();

        $conn->close();

        echo json_encode(['result' => 'ok', 'dataset' => $stat_name]);
        break;

    case 'envia':
        if (!user_is_logged_in()) {
            http_response_code(403);
            echo json_encode(['error' => 'No ha iniciado sesión']);
            break;
        }

        $user_id = get_user_id();
        $stat_name = trim($_POST['stat_name'] ?? '');
        $etiqueta = trim($_POST['etiqueta'] ?? '');
        $valor = trim($_POST['valor'] ?? '');

        if (!$stat_name || !is_valid_stat_name($stat_name)) {
            echo json_encode(['error' => 'Nombre de estadística inválido.']);
            break;
        }
        if (!$etiqueta) {
            echo json_encode(['error' => 'La etiqueta no puede estar vacía.']);
            break;
        }
        if (!is_numeric($valor)) {
            echo json_encode(['error' => 'El valor debe ser un número válido.']);
            break;
        }

        $conn = get_db_conn();
        $stmt = $conn->prepare("SELECT COUNT(*) as cnt FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        if ($row['cnt'] == 0) {
            $conn->close();
            echo json_encode(['error' => 'No existe esta estadística para el usuario actual.']);
            break;
        }

        $table_name = full_table_name($user_id, $stat_name);
        $stmt = $conn->prepare("INSERT INTO \"$table_name\" (etiqueta, valor) VALUES (?,?)");
        $stmt->bindValue(1, $etiqueta, SQLITE3_TEXT);
        $stmt->bindValue(2, floatval($valor), SQLITE3_FLOAT);
        $stmt->execute();

        $conn->close();

        echo json_encode(['resultado' => 'ok']);
        break;

    case 'labels_for_dataset':
        if (!user_is_logged_in()) {
            echo json_encode([]);
            break;
        }
        $user_id = get_user_id();
        $stat_name = trim($_GET['stat_name'] ?? '');
        if (!$stat_name || !is_valid_stat_name($stat_name)) {
            echo json_encode([]);
            break;
        }
        $conn = get_db_conn();
        $stmt = $conn->prepare("SELECT COUNT(*) as cnt FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        if ($row['cnt'] == 0) {
            $conn->close();
            echo json_encode([]);
            break;
        }
        $table_name = full_table_name($user_id, $stat_name);
        $res = $conn->query("SELECT etiqueta FROM \"$table_name\"");
        $labels = [];
        while ($r = $res->fetchArray(SQLITE3_ASSOC)) {
            $labels[] = $r['etiqueta'];
        }
        $conn->close();
        echo json_encode($labels);
        break;

    case 'delete_record':
        if (!user_is_logged_in()) {
            http_response_code(403);
            echo json_encode(['error' => 'No ha iniciado sesión']);
            break;
        }
        $user_id = get_user_id();
        $stat_name = trim($_POST['stat_name'] ?? '');
        $etiqueta = trim($_POST['etiqueta'] ?? '');

        if (!$stat_name || !is_valid_stat_name($stat_name)) {
            echo json_encode(['error' => 'Nombre de estadística inválido']);
            break;
        }
        if (!$etiqueta) {
            echo json_encode(['error' => 'La etiqueta no puede estar vacía.']);
            break;
        }

        $conn = get_db_conn();
        $stmt = $conn->prepare("SELECT COUNT(*) as cnt FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        if ($row['cnt'] == 0) {
            $conn->close();
            echo json_encode(['error' => 'No existe esta estadística para el usuario actual']);
            break;
        }

        $table_name = full_table_name($user_id, $stat_name);
        $stmt = $conn->prepare("DELETE FROM \"$table_name\" WHERE etiqueta=?");
        $stmt->bindValue(1, $etiqueta, SQLITE3_TEXT);
        $stmt->execute();
        $conn->close();

        echo json_encode(['result' => 'ok']);
        break;

    case 'update_record':
        if (!user_is_logged_in()) {
            http_response_code(403);
            echo json_encode(['error' => 'No ha iniciado sesión']);
            break;
        }

        $user_id = get_user_id();
        $stat_name = trim($_POST['stat_name'] ?? '');
        $etiqueta = trim($_POST['etiqueta'] ?? '');
        $valor = trim($_POST['valor'] ?? '');

        if (!$stat_name || !is_valid_stat_name($stat_name)) {
            echo json_encode(['error' => 'Nombre de estadística inválido']);
            break;
        }
        if (!$etiqueta) {
            echo json_encode(['error' => 'La etiqueta no puede estar vacía.']);
            break;
        }
        if (!is_numeric($valor)) {
            echo json_encode(['error' => 'El valor debe ser un número válido']);
            break;
        }

        $conn = get_db_conn();
        $stmt = $conn->prepare("SELECT COUNT(*) as cnt FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        if ($row['cnt'] == 0) {
            $conn->close();
            //echo json_encode({'error': 'No existe esta estadística para el usuario actual'});
            echo json_encode(array('error' => 'No existe esta estadística para el usuario actual'));

            break;
        }

        $table_name = full_table_name($user_id, $stat_name);
        $stmt = $conn->prepare("UPDATE \"$table_name\" SET valor=? WHERE etiqueta=?");
        $stmt->bindValue(1, floatval($valor), SQLITE3_FLOAT);
        $stmt->bindValue(2, $etiqueta, SQLITE3_TEXT);
        $stmt->execute();
        if ($conn->changes() == 0) {
            $conn->close();
            echo json_encode(['error' => 'No se encontró un registro con esa etiqueta']);
            break;
        }
        $conn->close();

        echo json_encode(['result' => 'ok']);
        break;

    case 'get_record_value':
        if (!user_is_logged_in()) {
            http_response_code(403);
            echo json_encode(['error' => 'No ha iniciado sesión']);
            break;
        }

        $user_id = get_user_id();
        $stat_name = trim($_GET['stat_name'] ?? '');
        $etiqueta = trim($_GET['etiqueta'] ?? '');

        if (!$stat_name || !is_valid_stat_name($stat_name)) {
            echo json_encode(['error' => 'Nombre de estadística inválido']);
            break;
        }
        if (!$etiqueta) {
            echo json_encode(['error' => 'La etiqueta no puede estar vacía']);
            break;
        }

        $conn = get_db_conn();
        $stmt = $conn->prepare("SELECT COUNT(*) as cnt FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        if ($row['cnt'] == 0) {
            $conn->close();
            echo json_encode(['error' => 'No existe esta estadística para el usuario actual']);
            break;
        }

        $table_name = full_table_name($user_id, $stat_name);
        $stmt = $conn->prepare("SELECT valor FROM \"$table_name\" WHERE etiqueta=?");
        $stmt->bindValue(1, $etiqueta, SQLITE3_TEXT);
        $res = $stmt->execute();
        $valrow = $res->fetchArray(SQLITE3_ASSOC);
        $conn->close();
        if (!$valrow) {
            echo json_encode(['error' => 'No se encontró un registro con esa etiqueta']);
            break;
        }

        echo json_encode(['value' => $valrow['valor']]);
        break;

    case 'delete_dataset':
        if (!user_is_logged_in()) {
            http_response_code(403);
            echo json_encode(['error' => 'No ha iniciado sesión']);
            break;
        }
        $user_id = get_user_id();
        $stat_name = trim($_POST['stat_name'] ?? '');

        if (!$stat_name || !is_valid_stat_name($stat_name)) {
            echo json_encode(['error' => 'Nombre de estadística inválido']);
            break;
        }

        $conn = get_db_conn();
        $stmt = $conn->prepare("SELECT COUNT(*) as cnt FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        if ($row['cnt'] == 0) {
            $conn->close();
            echo json_encode(['error' => 'No existe esta estadística para el usuario actual']);
            break;
        }

        $stmt = $conn->prepare("DELETE FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $stmt->execute();

        $table_name = full_table_name($user_id, $stat_name);
        $conn->exec("DROP TABLE IF EXISTS \"$table_name\"");

        $conn->close();

        echo json_encode(['result' => 'ok']);
        break;

    case 'get_dataset_config':
        if (!user_is_logged_in()) {
            http_response_code(403);
            echo json_encode(['error' => 'No ha iniciado sesión']);
            break;
        }
        $user_id = get_user_id();
        $stat_name = trim($_GET['stat_name'] ?? '');
        if (!$stat_name || !is_valid_stat_name($stat_name)) {
            echo json_encode(['error' => 'Nombre de estadística inválido']);
            break;
        }
        $conn = get_db_conn();
        $stmt = $conn->prepare("SELECT chart_type, chart_color FROM dataset_config WHERE user_id=? AND stat_name=?");
        $stmt->bindValue(1, $user_id, SQLITE3_INTEGER);
        $stmt->bindValue(2, $stat_name, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        $conn->close();
        if (!$row) {
            echo json_encode(['error' => 'No existe esta estadística para el usuario actual']);
            break;
        }
        echo json_encode(['chart_type' => $row['chart_type'], 'chart_color' => $row['chart_color']]);
        break;

    default:
        echo json_encode(['error' => 'No se especificó una acción válida']);
        break;
}


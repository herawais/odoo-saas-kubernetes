'use strict';
var FETCH_SIZE = 10000;
var FETCH_INTERVAL_TIME = 5000;
var AUTO_PAUSE_TIME = 1000 * 60 * 5;

function fetch_logs(begin, end) {
    return $.ajax({
        dataType: "text",
        cache: false,
        headers: {Range: 'bytes=' + (begin === false ? '' : begin) + '-' + (end === false ? '' : end)},
    }).then(function (data, s, xhr) {
        data = data.replace(/^\n/, "");
        data = data.replace(/\n$/, "");
        var content_range = xhr.getResponseHeader("Content-Range");
        var bytes = content_range ? /bytes ([0-9]*)-([0-9]*)\/([0-9]*)/.exec(content_range) : undefined;
        var begin = bytes ? parseInt(bytes[1]) : 0;
        var end = bytes ? parseInt(bytes[2]) : data.length;
        var size = bytes ? parseInt(bytes[3]) : data.length + 1;
        return {
            data: data,
            begin: begin,
            end: end,
            size: size,
        };
    });
}

$(document).ready(function () {
    var fetch_interval;
    var min;
    var max;
    var auto_scroll = true;
    var def_top;
    var def_bottom;

    function init() {
        $('.o-logs span').remove();
        return fetch_logs(false, 1).then(function (result) {
            min = max = Math.max(0, result.size - FETCH_SIZE);
            def_bottom = def_top = undefined;
        });
    }

    // borrowed from https://github.com/janl/mustache.js/blob/master/mustache.js
    function _escapeHTML(string) {
        var entityMap = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
            '/': '&#x2F;',
            '`': '&#x60;',
            '=': '&#x3D;'
        };
        return String(string).replace(/[&<>"'`=\/]/g, function fromEntityMap(s) {
            return entityMap[s];
        });
    }

    function _prepare_line(line) {
        var result = '<span class="o-log-line">'
        line.split('\n').forEach(function (l) {
            result += '<span style="white-space: pre;">' + _escapeHTML(l) + '</span><br/>';
        });
        result += '</span>'
        result = $(result);
        filter(result);
        return result;
    }

    function append_logs() {
        if (!def_bottom || def_bottom.state() !== 'pending') {
            def_bottom = fetch_logs(max, false).then(function (result) {
                if (max !== result.end) {
                    max = result.end;
                    var splits = result.data.split(/\s+(?=[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3})/)
                    splits.forEach(function (line) {
                        $('.o-logs').append(_prepare_line(line));
                    });
                    if (auto_scroll) {
                        window.scrollTo(0, document.body.scrollHeight);
                    }
                }
            }).fail(function (xhr) {
                if (xhr.status === 416) {
                    return init();
                }
            });
        }
        return def_bottom;
    }

    function prepend_logs() {
        if (min > 0 && (!def_top || def_top.state() !== 'pending')) {
            def_top = fetch_logs(Math.max(0, min - FETCH_SIZE), min).then(function (result) {
                min = result.begin;
                var lines = result.data.split('\n');
                var first_line = lines.pop();
                if (first_line) {
                    $('.o-logs span').first().prepend(_escapeHTML(first_line));
                }
                lines.reverse();
                lines.forEach(function (line) {
                    $('.o-logs').prepend(_prepare_line(line));
                });
                window.scrollTo(0, 20);
            }).fail(function (xhr) {
                if (xhr.status === 416) {
                    return init();
                }
            });
        }
        return def_top;
    }

    function toggle_pause() {
        $('i').toggle();
        $('.loader').toggleClass('loading');
        if (fetch_interval) {
            clearInterval(fetch_interval);
            fetch_interval = undefined;
        } else {
            fetch_interval = setInterval(append_logs, FETCH_INTERVAL_TIME);
            setTimeout(toggle_pause, AUTO_PAUSE_TIME);
        }
    }

    function filter(elements) {
        var filter = $('#filter').val();
        elements.filter(':contains(' + filter + ')').show();
        elements.filter(':not(:contains(' + filter + '))').hide();
    }

    $(window).scroll(function () {
        if ($(window).scrollTop() + $(window).height() === $(document).height()) {
            auto_scroll = true;
        } else {
            auto_scroll = false;
        }
        if ($(window).scrollTop() === 0) {
            prepend_logs();
        }
    });

    function fill_page() {
        if (!def_bottom) {
            append_logs().then(fill_page);
        } else if ($(window).height() === $(document).height() && min != 0 && (!def_top || def_top.state() !== 'pending')) {
            prepend_logs().then(fill_page);
        } else {
            $(window).scrollTop($(document).height());
        }
    }

    init().then(function () {
        fill_page();
        toggle_pause();
    });
    $('.button-pause').click(toggle_pause);
    $('#filter').on('input', function () {
        filter($('.o-logs .o-log-line'));
    });
    $('#filter').keypress(function (event) {
        if (event.keyCode === 10 || event.keyCode === 13) {
            event.preventDefault();
        }
    });
});

let ANNOTATION_FPS = 1

function seekToStep(container, step) {
    let video = container.find("video")[0];
    video.currentTime = container.find(`.timeline-step-${step}`).attr('data-time');
}

function getContainer(elem) {
    return elem.closest('.to-label-container');
}

function drawBoxes(container, step) {
    // Find any active boxes to draw at step `step`
    // Draw boxes to canvas
    let canvas = container.find('canvas')[0]
    let ctx = canvas.getContext('2d');

    let activeBoxes = container.find('.box-element-active');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const boxElem of activeBoxes) {
        jBoxElem = $(boxElem);
        let videoSelector = jBoxElem.attr('data-video');
        let boxId = jBoxElem.attr('data-box-id');
        let boxInfo = videoBoxes[videoSelector][boxId];
        if (step in boxInfo['boxes']) {
            let box = boxInfo['normalizedBoxes'][step];
            ctx.globalAlpha = 0.3;
            ctx.beginPath();
            ctx.fillStyle = boxInfo['color'];
            ctx.rect(
              box[0] * canvas.width,
              box[1] * canvas.height,
              box[2] * canvas.width,
              box[3] * canvas.height
            );
            ctx.fill();
            ctx.closePath();

            ctx.globalAlpha = 0.9;
            ctx.beginPath();
            ctx.strokeStyle = boxInfo['color'];
            ctx.lineWidth = 3;
            ctx.rect(
              box[0] * canvas.width,
              box[1] * canvas.height,
              box[2] * canvas.width,
              box[3] * canvas.height
            );
            ctx.stroke();
            ctx.closePath();
        }
    }
}

function playVideoSteps(container) {
    let previousInterval = container.data().playInterval;
    if (previousInterval !== undefined) {
        clearInterval(previousInterval);
        container.removeData('playInterval');
    }
    let jVideo = container.find('video'),
        video = jVideo[0];

    video.pause();
    jVideo.removeAttr('controls');
    let step = 0;
    let numSteps = container.find('.timeline-step-valid').length;
    let interval = setInterval(function() {
        if (step == numSteps) {
            step = 0;
        }
        let stepElement = container.find(`.timeline-step-valid`).eq(step);
        video.currentTime = stepElement.attr("data-time");
        step++;
    }, 1000);
    container.data('playInterval', interval);
}

function selectBox(boxElement) {
    let jBox = $(boxElement);
    jBox.siblings('.box-element').removeClass('box-element-active');
    jBox.addClass('box-element-active');

    // Set all timeline steps to be invalid
    let container = getContainer(jBox);
    let timeline = container.find('.timeline');
    timeline.find(".timeline-step").removeClass("timeline-step-valid");

    // Set valid timeline steps for this box
    let video = jBox.attr('data-video');
    let boxid = jBox.attr('data-box-id');
    let boxSteps = Object.keys(videoBoxes[video][boxid]['boxes']);
    boxSteps.forEach(i =>
        timeline.find(`.timeline-step-${i}`).addClass("timeline-step-valid")
    );

    // Start playing the video.
    playVideoSteps(container);
}

$(function() {
    $('canvas').each(function() {
        let jThis = $(this);
        let video = jThis.siblings('video');
        jThis.attr({
          height: video[0].videoHeight,
          width: video[0].videoWidth
        });
    });

    for (const [video, boxes] of Object.entries(videoBoxes)) {
        let videoSelector = $.escapeSelector(video);
        let videoElem = $(`#${videoSelector} video`)[0];
        for (const [boxId, boxInfo] of Object.entries(boxes)) {
            let boxSteps = boxInfo['boxes']
            let normalized = {}
            Object.entries(boxSteps).forEach(function([step, box]) {
                normalized[step] = [
                  box[0] / videoElem.videoWidth,
                  box[1] / videoElem.videoHeight,
                  box[2] / videoElem.videoWidth,
                  box[3] / videoElem.videoHeight
                ];
            })
            boxInfo['normalizedBoxes'] = normalized;
        }
        let boxHtml = Object.keys(boxes)
          .map(
            boxid => `<div data-video='${video}'
                           data-box-id='${boxid}'
                           id='${video}_${boxid}'
                           style='--color: ${boxes[boxid]["color"]}'
                           class='box-element'>
                      <div class='box-name'>${boxid}</div>
                      <select id='${video}_${boxid}-label'
                             name='${video}__${boxid}'
                             class='box-label'>
                             <option disabled selected value> -- label -- </option>
                            </select>
                      </div>`)
          .join("\n");
        $(`#${videoSelector} .boxes`).append(boxHtml);
        if (!videoSteps.hasOwnProperty(video)) {
            videoSteps[video] = {};
            let videoElem = $(`#${videoSelector} video`)[0]
            let numSteps = Math.round(videoElem.duration * ANNOTATION_FPS);
            for (let i = 0; i < numSteps; ++i) {
                videoSteps[video][i] = videoElem.duration / numSteps * i;
            }
        }
    }
    $('.box-element').addClass('box-element-active');

    $('.box-label').focus(function() {
        selectBox($(this).closest('.box-element')[0]);
    });
    $('.box-element').click(function() { selectBox(this); });

    for (const video in videoSteps) {
        let videoSelector = $.escapeSelector(video);
        let timeline = $(`#${videoSelector} .timeline`);
        for (const step in videoSteps[video]) {
            timeline.append(
              `<div data-time='${videoSteps[video][step]}'
                    data-step='${step}'
                    class='timeline-step timeline-step-${step}
                        timeline-step-valid'></div>`
            );
        }
    }

    $('.timeline-step').click(function() {
        let jThis = $(this);
        let step = jThis.attr('data-step');
        let container = getContainer(jThis);
        seekToStep(container, step);
        drawBoxes(container, step);
    })

    $('.play-steps').click(function() {
        playVideoSteps(getContainer($(this)));
    })

    // This will only trigger when controls are off, i.e., when we are playing
    // the video automatically at steps.
    $('video').unbind('click');
    $('video').click(function() {
        let container = getContainer($(this));
        let previousInterval = container.data('playInterval');
        if (previousInterval !== undefined) {
            clearInterval(previousInterval);
            container.removeData('playInterval');
            this.pause();
        }
        $('video').attr('controls', '');
        return false;
    });

    $('video').bind('timeupdate', function() {
        let container = getContainer($(this));
        container.find('.timeline-step').removeClass('timeline-step-active');
        let time = this.currentTime;
        let step = Math.round(time * Math.round(this.duration) / this.duration);
        container
          .find(`.timeline-step-${step}`)
          .addClass("timeline-step-active");
        drawBoxes(container, step);
    })

    $('form').unbind('submit');
    $('form').submit(function() {
        let emptyLabels = $(".box-label").filter(function() {
            return $.trim($(this).val()).length == 0;
        });

        if (emptyLabels.length == 0) {
            $('#error').hide();
            return true;
        } else {
            $("input.box-label").removeClass("container-error");
            emptyLabels.addClass("container-error");

            getContainer($("input.box-label")).removeClass("container-error");
            getContainer(emptyLabels).addClass("container-error");
            if (emptyLabels.length == 1) {
                $("#error").html("One box is unlabeled, please fix.");
            } else {
            $("#error").html(
                emptyLabels.length + " boxes unlabeled, please fix.");
            }
            $('#error').show()
            return false;
        }
    });

    function selectMatcher(params, data) {
        // If there are no search terms, return all of the data
        if ($.trim(params.term) === '') {
          return data;
        }

        // Do not display the item if there is no 'text' property
        if (typeof data.text === 'undefined') {
          return null;
        }

        // `params.term` should be the term that is used for searching
        // `data.text` is the text that is displayed for the data object
        let query = params.term.toLowerCase();
        let keys = ['name', 'synset', 'synonyms', 'def'];
        let rank = -1;
        for (let i = 0; i < keys.length; ++i) {
            if (!data.hasOwnProperty(keys[i])) {
                continue;
            }
            let value = '';
            if (keys[i] == 'synonyms') {
                value = data[keys[i]].join(' ');
            } else {
                value = data[keys[i]];
            }
            if (value.toLowerCase().indexOf(query) > -1) {
                rank = keys.length - i;
                break;
            }
        }
        if (rank != -1 || !data.hasOwnProperty('name')) {
            var modifiedData = $.extend(
            {
                rank: rank
            }, data, true);
            // You can return modified objects from here
            // This includes matching the `children` how you want in nested data sets
            return modifiedData;
        }
        return null;
    }

    function selectSorter(data) {
        if (data[1].rank && !data[0].rank) {
            // For tags
            data[0].rank = -1;
        }
        if (data && data.length > 1 && data[0].rank) {
          data.sort(function(a, b) {
            return a.rank > b.rank ? -1 : b.rank > a.rank ? 1 : 0;
          });
        }
        return data;
    }

    function selectTemplater(state) {
        if (!state.id) {
          return state.text;
        }

        if (!state.synset) {
            return state.text;
        }

        var $state = $(
          `<span class='select2-word-synset'>${state.synset}</span>
          <span class='select2-word-name'>(${state.name})</span>
          <div class='select2-word-def'>${state.def}</div>
          <div class='select2-word-synonyms'>Synonyms: ${state.synonyms}</div>`);
        return $state;
      };

    $('select.box-label').each(function() {
        $(this).select2({
          tags: true,
          data: categories,
          matcher: selectMatcher,
          sorter: selectSorter,
          templateResult: selectTemplater
        });
    });

    // https://stackoverflow.com/a/49261426/1291812
    // on first focus (bubbles up to document), open the menu
    $(document).on('focus', '.select2-selection.select2-selection--single',
    function (e) {
        $(this)
          .closest(".select2-container")
          .siblings("select:enabled")
          .select2("open");

        selectBox($(this).closest('.box-element')[0]);
    });

    // steal focus during close - only capture once and stop propogation
    $('select.select2').on('select2:closing', function (e) {
        $(e.target).data("select2").$selection.one('focus focusin',
            function (e) {
                e.stopPropagation();
            });
    });
});

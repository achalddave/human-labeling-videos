let ANNOTATION_FPS = 1

// Useful functions for console:
// 1. Set all selects to skip:
//    $('select').append(`<option value="skip">skip</option>`).val('skip')

function skipAll() {
    let confirmed = confirm('Skip all tracks?');
    if (confirmed) {
        $('select').append(`<option value='skip'>skip</option>`).val('skip')
    }
}

function getVideoKey(elem) {
    return elem.closest('.data-label-container').attr('id');
}

function seekToStep(container, step) {
    let video = container.find("video")[0];
    video.currentTime = container
      .find(`.timeline-step-${step}`)
      .attr("data-time");
}

function getStepOffset(container, stepOffset) {
    // Seek to offset stepOffset from current step. If there is no current step,
    // seek to step 0.
    let activeStep = container.find('.timeline-step-active');
    let nextStep;
    if (activeStep.length == 0) {
        nextStep = 0;
    } else {
        let currentStep = parseInt(activeStep.attr('data-step'));
        nextStep = currentStep + stepOffset;
        let numSteps = container.find('.timeline-step').length;
        if (nextStep < 0) {
            nextStep = numSteps - nextStep;
        } else if (nextStep >= numSteps) {
            nextStep = nextStep % numSteps;
        }
    }
    return nextStep;
}

function getContainer(elem) {
    return elem.closest('.to-label-container');
}

function getActiveContainer() {
    return $('.data-label-container.active').find('.to-label-container');
}

function drawBoxesHelper(canvas, activeBoxes, step) {
    let ctx = canvas.getContext('2d');
    ctx.fillStyle = 'black';
    // if (activeBoxes.length > 0) {
    //     ctx.globalAlpha = 0.1;
    //     ctx.rect(0, 0, canvas.width, canvas.height);
    //     ctx.fill();
    // }
    for (const boxElem of activeBoxes) {
        jBoxElem = $(boxElem);
        let videoSelector = jBoxElem.attr('data-video');
        let boxId = jBoxElem.attr('data-box-id');
        let boxInfo = videoBoxes[videoSelector][boxId];
        if (step in boxInfo['boxes']) {
            let box = boxInfo['normalizedBoxes'][step];
            ctx.globalAlpha = 0.1;
            ctx.beginPath();
            ctx.fillStyle = boxInfo['color'];
            [x0, y0, w, h] = [
              box[0] * canvas.width,
              box[1] * canvas.height,
              box[2] * canvas.width,
              box[3] * canvas.height
            ];
            ctx.rect(x0, y0, w, h);
            ctx.fill();
            ctx.closePath();

            ctx.globalAlpha = 0.9;
            ctx.beginPath();
            ctx.strokeStyle = boxInfo['color'];
            ctx.lineWidth = 3;
            ctx.rect(x0, y0, w, h);
            ctx.stroke();
            ctx.closePath();
        }
    }
}

function drawBoxes(container, step, drawOriginalFrame) {
    if (drawOriginalFrame === undefined) {
        drawOriginalFrame = false;
    }

    // Find any active boxes to draw at step `step`
    // Draw boxes to canvas
    let canvas = container.find('canvas')[0]
    let ctx = canvas.getContext('2d');

    let video = container.find('video')[0]
    if (canvas.width != video.videoWidth) {
        setupCanvas(canvas);
    }

    let activeBoxes = container.find('.box-element-active');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (drawOriginalFrame) {
        // https://stackoverflow.com/a/4776378/1291812
        let videoName = getVideoKey(container);
        let img = videoStepImages[videoName][step];
        let imgLoaded = img.complete && img.naturalHeight !== 0;
        if (imgLoaded) {
            ctx.globalAlpha = 1.0;
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            drawBoxesHelper(canvas, activeBoxes, step);
        } else {
            img.onload = function() {
                ctx.globalAlpha = 1.0;
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                drawBoxesHelper(canvas, activeBoxes, step);
            };
        }
    } else {
        drawBoxesHelper(canvas, activeBoxes, step);
    }

}

function stopStepPlayback(container) {
    let handler = container.data().playTimeout;
    if (handler !== undefined) {
        clearRequestTimeout(handler);
        container.removeData('playTimeout');
        return true;
    }
    return false;
}

function playVideoSteps(container) {
    stopStepPlayback(container);
    let jVideo = container.find('video'),
        video = jVideo[0];

    video.pause();
    jVideo.removeAttr('controls');
    let step = 0;
    let numSteps = container.find('.timeline-step-valid').length;
    function nextStep() {
        if (video.seeking) {
            let handler = requestTimeout(nextStep, 100);
            container.data('playTimeout', handler);
            return;
        }
        if (step == numSteps) {
            step = 0;
        }
        let stepElement = container.find(`.timeline-step-valid`).eq(step);
        video.currentTime = stepElement.attr("data-time");
        step++;
        let handler = requestTimeout(nextStep, 500);
        container.data('playTimeout', handler);
    }
    nextStep();
}

function selectBox(boxElement) {
    let jBox = $(boxElement);
    if ((jBox.hasClass('box-element-active')
        && $('.box-element-active').length == 1)) {
        return;
    }
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
    // playVideoSteps(container);
    console.log('Setting time')
    let jVideo = container.find('video');
    jVideo[0].pause();
    seekToStep(container, boxSteps[0]);
    jVideo[0].play();
}

function setupCanvas(canvas) {
    let jCanvas = $(canvas);
    let video = jCanvas.siblings('video');
    let vh = video[0].videoHeight, vw = video[0].videoWidth;
    jCanvas.attr({
        height: vh,
        width: vw
    });
    let videoName = getContainer(jCanvas).parent().attr('id');
    normalizeBoxes(videoName);

    /*
    // 
    // For portrait videos, fill the height. For landscape videos, fill
    // the width. If we instead indiscriminately set height: 100%, and
    // max-width to 100%, then the videos themselves will look fine, but
    // the canvas and the video container will be taller than the actual
    // video for landscape (wide) videos, which leads to a mismatch in
    // the canvas location and video location.
    if (vh > vw) {
        video.css('height', '100%');
        jThis.css('height', '100%');
    } else {
        video.css('width', '100%');
        jThis.css('width', '100%');
    }
    */
}

function normalizeBoxes(videoName) {
    let videoSelector = $.escapeSelector(videoName);
    let videoElem = $(`#${videoSelector} video`)[0];
    let boxes = videoBoxes[videoName];
    for (const [_, boxInfo] of Object.entries(boxes)) {
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
}

$(function() {
    if ($('.data-label-container').length == 0) {
        $('body').append('<h1 class="congrats">Congratulations. You\'re done!</h1>')
        $('body').css('background', 'black');
        $('body').append('<canvas id="fireworks">');
        var s = document.createElement('script');
        s.setAttribute('src', 'static/fireworks.js');
        s.onload = function() { loop(); };
        document.body.appendChild(s);
    }

    for (const [video, boxes] of Object.entries(videoBoxes)) {
        console.log('boxes', boxes);
        console.log(`Found ${Object.keys(boxes).length} boxes.`)
        let videoSelector = $.escapeSelector(video);
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
        console.log('Appending boxHtml');
        $(`#${videoSelector} .boxes`).append(boxHtml);
        console.log(video);
        console.log(videoSteps);
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
    $('.box-element').click(function(e) {
        if (e.ctrlKey || e.metaKey) {
            $(this).toggleClass('box-element-active');
        } else {
            selectBox(this);
        }
    });

    window.videoStepImages = {}
    for (const video in videoSteps) {
        let videoSelector = $.escapeSelector(video);
        let timeline = $(`#${videoSelector} .timeline`);
        videoStepImages[video] = {};
        for (const step in videoSteps[video]) {
            let parts = videoStepFrames[video][step].split('/');
            let frameName = parts[parts.length - 1];
            let title = `frame=${frameName}, t=${videoSteps[video][step]}`;
            timeline.append(
              `<div data-time='${videoSteps[video][step]}'
                    data-step='${step}'
                    title='${title}'
                    class='timeline-step timeline-step-${step}
                        timeline-step-valid'></div>`
            );
            // Preload step image
            let image = new Image;
            image.src = videoStepFrames[video][step];
            videoStepImages[video][step] = image;
        }
    }

    $('.timeline-step').click(function() {
        let jThis = $(this);
        let step = jThis.attr('data-step');
        let container = getContainer(jThis);
        seekToStep(container, step);
        // drawBoxes(container, step, /*drawOriginalFrame=*/true);
    })

    $('.play-steps').click(function() {
        playVideoSteps(getContainer($(this)));
    })

    $('video').each(function() {
        if (this.readyState == 4) {  // Already loaded
            setupCanvas(getContainer($(this)).find('canvas')[0]);
        }
    });


    // This will only trigger when controls are off, i.e., when we are playing
    // the video automatically at steps.
    $('video').unbind('click');
    $('video').click(function() {
        stopStepPlayback(getContainer($(this)));
        this.pause();
        $('video').attr('controls', '');
        return false;
    });

    $('video').bind('timeupdate', function() {
        let jThis = $(this);
        let container = getContainer(jThis);
        container.find('.timeline-step').removeClass('timeline-step-active');
        let videoName = getVideoKey(container);
        let time = this.currentTime;
        let closestStep, closestStepDistance = Infinity;
        for ([step, stepTime] of Object.entries(videoSteps[videoName])) {
            let dist = Math.abs(stepTime - time)
            if (dist < closestStepDistance) {
                closestStepDistance = dist;
                closestStep = step;
            }
        }

        // // Pause once when we get close to the frame of interest. After that,
        // // skip ahead so we don't pause again.
        // let thresh = 0.05;
        // if (!this.paused && closestStepDistance < thresh) {
        //     this.pause();
        //     seekToStep(container, videoSteps[videoName][closestStep]);
        //     setTimeout(() => {
        //         this.currentTime = time + thresh;
        //         this.play();
        //     }, 300);
        // }

        container
          .find(`.timeline-step-${closestStep}`)
          .addClass("timeline-step-active");
        // If we are close to a step and the video is paused, draw the original
        // annotated frame image on the canvas.
        let thresh = 0.05;
        let drawOriginalFrame = (this.paused && closestStepDistance < thresh)
        drawBoxes(container, closestStep, drawOriginalFrame);
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


    let boxSelects = $('select.box-label');
    function setupSelect2(elem) {
        elem.select2({
                    tags: true,
                    data: categories,
                    matcher: selectMatcher,
                    sorter: selectSorter,
                    templateResult: selectTemplater
                })
    }
    // If there are many boxes, only initialize select2 when focused.
    if (boxSelects.length > 20) {
      boxSelects.focus(function() {
        if (!$(this).hasClass("select2-hidden-accessible")) {
          setupSelect2($(this));
          $(this).focus();
        }
      });
    } else {
      setupSelect2(boxSelects);
    }
    // $('select.box-label').select2({
    // });
    // $('select.box-label').each(function() {
    //     $(this).select2({
    //       tags: true,
    //       data: categories,
    //       matcher: selectMatcher,
    //       sorter: selectSorter,
    //       templateResult: selectTemplater
    //     });
    // });

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

    window.addEventListener("unhandledKey", event => {
      let rawEvent = event;
      event = rawEvent.detail;  // original key event
      let container = getActiveContainer();
      if (event.key == '[' || event.key == ']') {
          stopStepPlayback(container);
          let jVideo = container.find('video');
          jVideo[0].pause();
          let offset = event.key == '[' ? -1 : 1;
          let nextStep = getStepOffset(container, offset);
          seekToStep(container, nextStep);
          // drawBoxes(container, nextStep, /*drawOriginalFrame=*/true);
      }
    });
});

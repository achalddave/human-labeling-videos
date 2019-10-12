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
        ctx.globalAlpha = 0.3;
        if (step in boxInfo['boxes']) {
            let box = boxInfo['normalizedBoxes'][step];
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
                      <input type='text' 
                             id='${boxid}-label'
                             name='${video}__${boxid}'
                             class='box-label'></input>
                      </div>`)
          .join("\n");
        $(`#${videoSelector} .boxes`).append(boxHtml);
    }
    $('.box-element').addClass('box-element-active');

    $('.box-label').focus(function() {
        selectBox($(this).closest('.box-element')[0]);
    });
    $('.box-element').click(function() { selectBox(this); });

    $('.timeline').each(function() {
        let container = $(this).closest(".to-label-container");
        let video = container.find("video")[0];
        let numSteps = Math.floor(video.duration);
        for (let i = 0; i < numSteps; ++i) {
            let time = video.duration / numSteps * i;
            $(this).append(
              `<div data-time='${time}'
                    data-step='${i}'
                    class='timeline-step timeline-step-${i}
                           timeline-step-valid'></div>`
            );
        }
    });

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
            console.log('Clearing interval from play/pause event');
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
        let step = Math.round(time * Math.floor(this.duration) / this.duration);
        container
          .find(`.timeline-step-${step}`)
          .addClass("timeline-step-active");
        drawBoxes(container, step);
    })

    $('form').unbind('submit');
    $('form').submit(function() {
        console.log('submitting');
        let emptyLabels = $("input.box-label").filter(function() {
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

});

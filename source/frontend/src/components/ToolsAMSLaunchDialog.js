import React, { Component } from "react";
import { ClipLoader, BeatLoader } from 'react-spinners';
import { css } from '@emotion/core';

const override = css`
  display: flex;
  justify-content: center;
  margin: 50px auto;
`;

export default class UserListColDialog extends Component {
  constructor(props) {
    super(props);

    this.state = {
      showDialog: this.props.showDialog,
      AMSmsg: this.props.AMSmsg,
      waitPeriod: this.props.waitPeriod,
    };
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      showDialog: nextProps.showDialog
    });
    this.setState({
      AMSmsg: nextProps.AMSmsg
    });
    this.setState({
      waitPeriod: nextProps.waitPeriod
    });
  }

  async componentDidMount() {
    this.timerID = setInterval(
      () => this.tick(),
      1000
    );
  }

  onClickCancelDialog = event => {
    this.setState({
      showDialog: false
    });
    this.props.onClickUpdate()
  }

  tick = async event => {
    const minutesSinceDisplay = Math.abs(Date.now() - this.lastActivity) / 1000 / 60;

    if (minutesSinceDisplay > this.timeout && this.state.waitPeriod) {
      this.setState({
        AMSmsg: 'Unexpected timeout. Please try again.',
        waitPeriod: false,
      });
    }
  }

  render() {
    let styles = this.state.showDialog
      ? { display: "block" }
      : { display: "none" };
    return (
      <div>

          <div>
            <div className="block-events-full"> </div>
            <div class="modal fade show" data-backdrop="static" style={styles} id="ModalCenter" tabindex="-1" role="dialog" aria-labelledby="ModalCenterTitle" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered" role="document">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="ModalLongTitle">
                <div className="pb-4">
                        <b>{(this.state.waitPeriod) ? 'Waiting for AWS Managed Services' : 'Response from AWS Managed Services'}</b>
                        {/* Only display exit button after response is received */}
                      </div>
                </h5>
              </div>
              <div class="modal-body">
              {this.state.AMSmsg}
              <BeatLoader
                            css={override}
                            sizeUnit={"px"}
                            size={15}
                            color={'#ec912d'}
                            loading={this.state.waitPeriod}
                          />
              </div>
              <div class="modal-footer">
              {!this.state.waitPeriod &&
                        <span onClick={this.onClickCancelDialog} className="onhover float-right"><button type="button" class="btn btn-primary" data-dismiss="modal">Close</button></span>
                        }
                
              </div>
            </div>
          </div>
        </div>
          </div>

    </div>
    )
  }
}

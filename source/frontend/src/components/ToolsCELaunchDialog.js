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

    // Time since page 
    this.lastActivity = Date.now();
    // Limit as to how many minutes API call takes before ruling it a timeout
    this.timeout = 45;

    this.state = {
      showDialog: this.props.showDialog,
      cloudenduremsg: this.props.cloudenduremsg,
      waitPeriod: this.props.waitPeriod,
    };
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      showDialog: nextProps.showDialog
    });
    this.setState({
      cloudenduremsg: nextProps.cloudenduremsg
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

  componentWillUnmount() {
    clearInterval(this.timerID);
  }

  onClickCancelDialog = event => {
    this.setState({
      showDialog: false
    });
    this.props.onClickUpdate()
  }

  tick = async event => {
    const minutesSinceDisplay = Math.abs(Date.now() - this.lastActivity) / 1000;

    if (minutesSinceDisplay > this.timeout && this.state.waitPeriod) {
      this.setState({
        cloudenduremsg: 'Unexpected timeout. Please try again.',
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
                        <b>{(this.state.waitPeriod) ? 'Waiting for CloudEndure' : 'Response from CloudEndure'}</b>
                        {/* Only display exit button after response is received */}
                      </div>
                </h5>
              </div>
              <div class="modal-body">
              {this.state.cloudenduremsg}
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
